from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import Institution, User

from ..domain.declaration_mapping import (
    ELIGIBLE_DISPOSITIONS,
    DeclarationChange,
    build_default_onboarding_declaration_mapping_registry,
    rejected_change,
)
from ..domain.enums import (
    AttributeClassification,
    AttributeSourceType,
    DeclarationChangeType,
    DeclarationFieldStatus,
    DeclarationSynchronizationResultCode,
    DeclarationSynchronizationStatus,
    EvidenceRelationship,
    EvidenceSourceDomain,
    EvidenceSourceType,
    LearningProfileStatus,
    ProfileVersionStatus,
    ProvenanceReadinessStatus,
)
from ..domain.models import (
    LearnerLearningProfile,
    LearningIdentityAttribute,
    LearningIdentityDeclarationSynchronization,
    LearningIdentityEvidenceLink,
    LearningProfileVersion,
)
from .evidence_services import LinkLearningIdentityEvidenceService
from .onboarding_dto import ConfirmedLearningIdentityDeclarationSet
from .onboarding_ports import ConfirmedOnboardingDeclarationSource
from .provenance import evaluate_profile_version_provenance
from .services import _ensure_actor_can_manage, _fingerprint


@dataclass(frozen=True)
class DeclarationPreviewResult:
    profile_exists: bool
    current_profile_status: str
    current_version_number: int | None
    incoming_onboarding_revision: int
    existing_draft_disposition: str
    provenance_readiness: str
    reason_codes: tuple[str, ...]
    would_publish: bool
    changes: tuple[DeclarationChange, ...]

    def safe_dict(self) -> dict[str, Any]:
        counts = Counter(change.change_type for change in self.changes)
        return {
            "profile_exists": self.profile_exists,
            "current_profile_status": self.current_profile_status,
            "current_version_number": self.current_version_number,
            "incoming_onboarding_revision": self.incoming_onboarding_revision,
            "existing_draft_disposition": self.existing_draft_disposition,
            "provenance_readiness": self.provenance_readiness,
            "reason_codes": list(self.reason_codes),
            "would_publish": self.would_publish,
            "change_counts": dict(sorted(counts.items())),
            "changes": [change.safe_dict() for change in self.changes],
        }


def _publish_after_commit(events: EventPublisher, event_name: str, payload: dict[str, Any]) -> None:
    transaction.on_commit(lambda: events.publish(BusinessEvent.create(event_name, payload=payload)))


def _source_identifier(declaration_set: ConfirmedLearningIdentityDeclarationSet) -> str:
    return f"{declaration_set.onboarding_session_id}:{declaration_set.onboarding_revision}"


def _declaration_fingerprint(declaration_set: ConfirmedLearningIdentityDeclarationSet, changes: tuple[DeclarationChange, ...]) -> str:
    payload = {
        "onboarding_session_id": declaration_set.onboarding_session_id,
        "onboarding_revision": declaration_set.onboarding_revision,
        "tenant_id": declaration_set.tenant_id,
        "learner_id": declaration_set.learner_id,
        "source_schema_version": declaration_set.source_schema_version,
        "changes": [
            {
                "source_field": change.source_field,
                "attribute_type": change.attribute_type,
                "normalized_value": change.normalized_value,
                "reason_codes": list(change.reason_codes),
                "restricted": change.restricted,
                "visibility": change.visibility,
            }
            for change in sorted(changes, key=lambda item: (item.source_field, item.attribute_type))
        ],
    }
    return _fingerprint(payload)


class OnboardingDeclarationPlanner:
    def __init__(self, *, mapping_registry=None):
        self.mapping_registry = mapping_registry or build_default_onboarding_declaration_mapping_registry()

    def plan(
        self,
        *,
        declaration_set: ConfirmedLearningIdentityDeclarationSet,
        profile: LearnerLearningProfile | None,
    ) -> DeclarationPreviewResult:
        current_version = profile.current_version if profile and profile.current_version_id else None
        current_by_type = {}
        if current_version:
            current_by_type = {
                attribute.attribute_type: attribute
                for attribute in current_version.attributes.order_by("attribute_type", "created_at")
                if attribute.classification == AttributeClassification.DECLARED
            }
        changes: list[DeclarationChange] = []
        reason_codes: set[str] = set()
        for declaration in sorted(declaration_set.declarations, key=lambda item: item.source_field):
            try:
                mapping = self.mapping_registry.get(declaration.source_field)
            except ValidationError:
                change = rejected_change(declaration.source_field, "UNSUPPORTED_ONBOARDING_FIELD")
                changes.append(change)
                reason_codes.update(change.reason_codes)
                continue
            if declaration.source_value_schema_version not in mapping.supported_source_schema_versions:
                change = rejected_change(declaration.source_field, "VALUE_SCHEMA_UNSUPPORTED")
                changes.append(change)
                reason_codes.update(change.reason_codes)
                continue
            if declaration.confirmation_disposition not in ELIGIBLE_DISPOSITIONS:
                change = rejected_change(declaration.source_field, "LEARNER_CONFIRMATION_REQUIRED")
                changes.append(change)
                reason_codes.update(change.reason_codes)
                continue
            current = current_by_type.get(mapping.target_attribute_type)
            if declaration.explicit_clear:
                change_type = DeclarationChangeType.CLEARED if current else DeclarationChangeType.UNCHANGED
                changes.append(
                    DeclarationChange(
                        source_field=declaration.source_field,
                        attribute_type=mapping.target_attribute_type,
                        change_type=change_type,
                        status=DeclarationFieldStatus.EXPLICITLY_CLEARED,
                        current_value_present=current is not None,
                        incoming_value_present=False,
                        visibility=mapping.default_visibility,
                        restricted=mapping.restricted,
                    )
                )
                continue
            try:
                normalized = mapping.normalize(declaration.raw_normalized_value)
            except ValidationError:
                change = rejected_change(declaration.source_field, "VALUE_NORMALIZATION_FAILED")
                changes.append(change)
                reason_codes.update(change.reason_codes)
                continue
            if current and mapping.equivalent(current.value, normalized):
                changes.append(
                    DeclarationChange(
                        source_field=declaration.source_field,
                        attribute_type=mapping.target_attribute_type,
                        change_type=DeclarationChangeType.UNCHANGED,
                        status=DeclarationFieldStatus.UNCHANGED,
                        current_value_present=True,
                        incoming_value_present=True,
                        visibility=current.visibility,
                        restricted=current.restricted,
                        normalized_value=normalized,
                    )
                )
            else:
                changes.append(
                    DeclarationChange(
                        source_field=declaration.source_field,
                        attribute_type=mapping.target_attribute_type,
                        change_type=DeclarationChangeType.UPDATED if current else DeclarationChangeType.ADDED,
                        status=DeclarationFieldStatus.ELIGIBLE,
                        current_value_present=current is not None,
                        incoming_value_present=True,
                        visibility=mapping.default_visibility,
                        restricted=mapping.restricted,
                        normalized_value=normalized,
                    )
                )

        draft_exists = bool(profile and profile.profile_versions.filter(status=ProfileVersionStatus.DRAFT).exists())
        material = any(change.change_type in {DeclarationChangeType.ADDED, DeclarationChangeType.UPDATED, DeclarationChangeType.CLEARED} for change in changes)
        if draft_exists and material:
            reason_codes.add(DeclarationSynchronizationResultCode.UNRELATED_DRAFT_EXISTS)
            existing_draft_disposition = "BLOCKED_BY_EXISTING_DRAFT"
        else:
            existing_draft_disposition = "NONE"
        if not changes:
            reason_codes.add("NO_ELIGIBLE_DECLARATIONS")
        blocked = any(change.change_type == DeclarationChangeType.BLOCKED for change in changes) or (
            draft_exists and material
        )
        readiness = ProvenanceReadinessStatus.READY if not blocked else ProvenanceReadinessStatus.BLOCKED
        return DeclarationPreviewResult(
            profile_exists=profile is not None,
            current_profile_status=profile.status if profile else "",
            current_version_number=profile.current_version.version_number if profile and profile.current_version_id else None,
            incoming_onboarding_revision=declaration_set.onboarding_revision,
            existing_draft_disposition=existing_draft_disposition,
            provenance_readiness=readiness,
            reason_codes=tuple(sorted(str(code) for code in reason_codes)),
            would_publish=material and readiness == ProvenanceReadinessStatus.READY,
            changes=tuple(changes),
        )


class PreviewOnboardingDeclarationChangesService:
    def __init__(
        self,
        *,
        source: ConfirmedOnboardingDeclarationSource | None = None,
        planner: OnboardingDeclarationPlanner | None = None,
    ):
        if source is None:
            raise ValueError("A confirmed onboarding declaration source port is required.")
        self.source = source
        self.planner = planner or OnboardingDeclarationPlanner()

    def execute(self, *, onboarding_session_id, onboarding_revision: int, tenant_id, learner_id, actor: User) -> DeclarationPreviewResult:
        _ensure_actor_can_manage(actor=actor, tenant_id=tenant_id, learner_id=learner_id)
        declaration_set = self.source.resolve_confirmed_declarations(
            onboarding_session_id=onboarding_session_id,
            onboarding_revision=onboarding_revision,
            tenant_id=tenant_id,
            learner_id=learner_id,
        )
        profile = (
            LearnerLearningProfile.objects.select_related("current_version")
            .filter(tenant_id=tenant_id, learner_id=learner_id)
            .exclude(status=LearningProfileStatus.ARCHIVED)
            .first()
        )
        return self.planner.plan(declaration_set=declaration_set, profile=profile)


class ApplyConfirmedOnboardingDeclarationsService:
    def __init__(
        self,
        *,
        source: ConfirmedOnboardingDeclarationSource | None = None,
        planner: OnboardingDeclarationPlanner | None = None,
        events: EventPublisher | None = None,
    ):
        if source is None:
            raise ValueError("A confirmed onboarding declaration source port is required.")
        self.source = source
        self.planner = planner or OnboardingDeclarationPlanner()
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(
        self,
        *,
        onboarding_session_id,
        onboarding_revision: int,
        tenant_id,
        learner_id,
        actor: User,
        source_event_id: str = "",
        idempotency_key: str = "",
        expected_profile_version: int | None = None,
    ) -> LearningIdentityDeclarationSynchronization:
        _ensure_actor_can_manage(actor=actor, tenant_id=tenant_id, learner_id=learner_id)
        declaration_set = self.source.resolve_confirmed_declarations(
            onboarding_session_id=onboarding_session_id,
            onboarding_revision=onboarding_revision,
            tenant_id=tenant_id,
            learner_id=learner_id,
        )
        profile = (
            LearnerLearningProfile.objects.select_for_update()
            .filter(tenant_id=tenant_id, learner_id=learner_id)
            .exclude(status=LearningProfileStatus.ARCHIVED)
            .first()
        )
        preview = self.planner.plan(declaration_set=declaration_set, profile=profile)
        fingerprint = _declaration_fingerprint(declaration_set, preview.changes)
        if existing := self._existing_receipt(declaration_set=declaration_set, fingerprint=fingerprint, idempotency_key=idempotency_key):
            return existing
        latest = (
            LearningIdentityDeclarationSynchronization.objects.filter(onboarding_session_id=onboarding_session_id)
            .order_by("-onboarding_revision", "-created_at")
            .first()
        )
        if latest and latest.onboarding_revision > onboarding_revision:
            raise ValidationError("Onboarding revision is stale.", code=DeclarationSynchronizationResultCode.ONBOARDING_REVISION_STALE)
        material_changes = [
            change
            for change in preview.changes
            if change.change_type in {DeclarationChangeType.ADDED, DeclarationChangeType.UPDATED, DeclarationChangeType.CLEARED}
        ]
        if not material_changes:
            receipt = self._receipt(
                declaration_set=declaration_set,
                profile=profile,
                profile_version=None,
                status=DeclarationSynchronizationStatus.NO_CHANGE,
                result_code=DeclarationSynchronizationResultCode.NO_CHANGE,
                readiness_status=ProvenanceReadinessStatus.READY,
                fingerprint=fingerprint,
                source_event_id=source_event_id or declaration_set.source_event_id,
                idempotency_key=idempotency_key,
                changes=preview.changes,
                reason_codes=preview.reason_codes,
            )
            if profile:
                self._publish_events(receipt=receipt, profile=profile, declaration_set=declaration_set, changes=preview.changes)
            return receipt
        if preview.existing_draft_disposition == "BLOCKED_BY_EXISTING_DRAFT":
            receipt = self._receipt(
                declaration_set=declaration_set,
                profile=profile,
                profile_version=None,
                status=DeclarationSynchronizationStatus.BLOCKED,
                result_code=DeclarationSynchronizationResultCode.UNRELATED_DRAFT_EXISTS,
                readiness_status=ProvenanceReadinessStatus.BLOCKED,
                fingerprint=fingerprint,
                source_event_id=source_event_id or declaration_set.source_event_id,
                idempotency_key=idempotency_key,
                changes=preview.changes,
                reason_codes=preview.reason_codes,
            )
            self._publish_events(receipt=receipt, profile=profile, declaration_set=declaration_set, changes=preview.changes)
            return receipt
        if profile is None:
            tenant = Institution.objects.get(id=tenant_id)
            learner = User.objects.get(id=learner_id)
            profile = LearnerLearningProfile.objects.create(tenant=tenant, learner=learner, status=LearningProfileStatus.DRAFT)
        elif expected_profile_version is not None and profile.version != expected_profile_version:
            raise ValidationError("Learning profile version conflict.", code=DeclarationSynchronizationResultCode.PROFILE_VERSION_CONFLICT)

        draft = self._create_draft(profile=profile, actor=actor, changed_attribute_types={change.attribute_type for change in material_changes})
        for change in material_changes:
            if change.change_type == DeclarationChangeType.CLEARED:
                continue
            attribute = self._create_attribute(draft=draft, change=change, actor=actor, declaration_set=declaration_set)
            self._link_onboarding_evidence(profile=profile, draft=draft, attribute=attribute, actor=actor, declaration_set=declaration_set)
            profile.refresh_from_db()
        if not draft.attributes.exists():
            receipt = self._receipt(
                declaration_set=declaration_set,
                profile=profile,
                profile_version=draft,
                status=DeclarationSynchronizationStatus.BLOCKED,
                result_code=DeclarationSynchronizationResultCode.PROVENANCE_BLOCKED,
                readiness_status=ProvenanceReadinessStatus.BLOCKED,
                fingerprint=fingerprint,
                source_event_id=source_event_id or declaration_set.source_event_id,
                idempotency_key=idempotency_key,
                changes=preview.changes,
                reason_codes=tuple(sorted({*preview.reason_codes, "PROFILE_VERSION_ATTRIBUTES_REQUIRED"})),
            )
            self._publish_events(receipt=receipt, profile=profile, declaration_set=declaration_set, changes=preview.changes)
            return receipt
        readiness = evaluate_profile_version_provenance(draft)
        result_code = DeclarationSynchronizationResultCode.APPLIED
        status = DeclarationSynchronizationStatus.APPLIED
        if readiness.status == ProvenanceReadinessStatus.READY:
            profile.refresh_from_db()
            from .services import PublishLearningProfileVersionService

            PublishLearningProfileVersionService(events=self.events).execute(
                profile_version_id=draft.id,
                actor=actor,
                expected_version=profile.version,
                idempotency_key=f"onboarding-publish:{declaration_set.onboarding_session_id}:{declaration_set.onboarding_revision}",
            )
            profile.refresh_from_db()
            _publish_after_commit(
                self.events,
                "learning_identity.profile_version.published_from_onboarding",
                self._event_payload(profile, declaration_set, draft, status),
            )
        elif readiness.status == ProvenanceReadinessStatus.NEEDS_REVIEW:
            result_code = DeclarationSynchronizationResultCode.PROVENANCE_REVIEW_REQUIRED
            status = DeclarationSynchronizationStatus.BLOCKED
        else:
            result_code = DeclarationSynchronizationResultCode.PROVENANCE_BLOCKED
            status = DeclarationSynchronizationStatus.BLOCKED
        receipt = self._receipt(
            declaration_set=declaration_set,
            profile=profile,
            profile_version=draft,
            status=status,
            result_code=result_code,
            readiness_status=readiness.status,
            fingerprint=fingerprint,
            source_event_id=source_event_id or declaration_set.source_event_id,
            idempotency_key=idempotency_key,
            changes=preview.changes,
            reason_codes=tuple(sorted({*preview.reason_codes, *readiness.blocking_codes, *readiness.review_codes})),
        )
        self._publish_events(receipt=receipt, profile=profile, declaration_set=declaration_set, changes=preview.changes)
        return receipt

    def _existing_receipt(self, *, declaration_set, fingerprint: str, idempotency_key: str):
        candidates = LearningIdentityDeclarationSynchronization.objects.filter(
            onboarding_session_id=declaration_set.onboarding_session_id,
            onboarding_revision=declaration_set.onboarding_revision,
        )
        if idempotency_key:
            candidates = candidates | LearningIdentityDeclarationSynchronization.objects.filter(idempotency_key=idempotency_key)
        existing = candidates.order_by("-created_at").first()
        if not existing:
            return None
        if existing.payload_fingerprint != fingerprint:
            raise ValidationError("Onboarding revision payload changed.", code=DeclarationSynchronizationResultCode.ONBOARDING_REVISION_PAYLOAD_CONFLICT)
        return existing

    def _receipt(self, *, declaration_set, profile, profile_version, status, result_code, readiness_status, fingerprint, source_event_id, idempotency_key, changes, reason_codes):
        now = timezone.now()
        counts = Counter(change.change_type for change in changes)
        receipt = LearningIdentityDeclarationSynchronization(
            profile=profile,
            profile_version=profile_version,
            tenant_id=declaration_set.tenant_id,
            learner_id=declaration_set.learner_id,
            onboarding_session_id=declaration_set.onboarding_session_id,
            onboarding_revision=declaration_set.onboarding_revision,
            source_event_id=source_event_id,
            payload_fingerprint=fingerprint,
            source_schema_version=declaration_set.source_schema_version,
            status=status,
            result_code=result_code,
            readiness_status=readiness_status,
            change_counts=dict(sorted(counts.items())),
            reason_codes=list(reason_codes),
            idempotency_key=idempotency_key,
            applied_at=now if status in {DeclarationSynchronizationStatus.APPLIED, DeclarationSynchronizationStatus.NO_CHANGE} else None,
            blocked_at=now if status == DeclarationSynchronizationStatus.BLOCKED else None,
            failed_at=now if status == DeclarationSynchronizationStatus.FAILED else None,
        )
        try:
            receipt.full_clean()
            receipt.save()
        except IntegrityError as exc:
            existing = LearningIdentityDeclarationSynchronization.objects.filter(
                onboarding_session_id=declaration_set.onboarding_session_id,
                onboarding_revision=declaration_set.onboarding_revision,
            ).first()
            if existing and existing.payload_fingerprint == fingerprint:
                return existing
            raise ValidationError("Onboarding revision payload changed.", code=DeclarationSynchronizationResultCode.ONBOARDING_REVISION_PAYLOAD_CONFLICT) from exc
        return receipt

    def _create_draft(self, *, profile, actor, changed_attribute_types: set[str]):
        next_number = (LearningProfileVersion.objects.filter(profile=profile).order_by("-version_number").values_list("version_number", flat=True).first() or 0) + 1
        draft = LearningProfileVersion.objects.create(profile=profile, version_number=next_number, created_by=actor)
        if profile.current_version_id:
            for attribute in profile.current_version.attributes.prefetch_related("evidence_links").order_by("attribute_type", "created_at"):
                if attribute.attribute_type in changed_attribute_types:
                    continue
                cloned = LearningIdentityAttribute.objects.create(
                    profile_version=draft,
                    attribute_type=attribute.attribute_type,
                    classification=attribute.classification,
                    value=attribute.value,
                    value_schema_version=attribute.value_schema_version,
                    confidence=attribute.confidence,
                    source_type=attribute.source_type,
                    source_reference=attribute.source_reference,
                    declared_at=attribute.declared_at,
                    valid_from=attribute.valid_from,
                    valid_until=attribute.valid_until,
                    visibility=attribute.visibility,
                    review_required=attribute.review_required,
                    restricted=attribute.restricted,
                    created_by=actor,
                )
                for link in attribute.evidence_links.order_by("created_at"):
                    LearningIdentityEvidenceLink.objects.create(
                        attribute=cloned,
                        source_domain=link.source_domain,
                        source_type=link.source_type,
                        source_identifier=link.source_identifier,
                        source_revision=link.source_revision,
                        relationship=link.relationship,
                        authority_class=link.authority_class,
                        status=link.status,
                        source_observed_at=link.source_observed_at,
                        valid_from=link.valid_from,
                        valid_until=link.valid_until,
                        freshness_expires_at=link.freshness_expires_at,
                        weight=link.weight,
                        confidence_contribution=link.confidence_contribution,
                        safe_summary=link.safe_summary,
                        summary_visibility=link.summary_visibility,
                        metadata_schema_version=link.metadata_schema_version,
                        linked_by=actor,
                        review_required=link.review_required,
                        reason_codes=link.reason_codes,
                    )
        profile.version += 1
        profile.save(update_fields=["version", "updated_at"])
        return draft

    def _create_attribute(self, *, draft, change, actor, declaration_set):
        attribute = LearningIdentityAttribute(
            profile_version=draft,
            attribute_type=change.attribute_type,
            classification=AttributeClassification.DECLARED,
            value=change.normalized_value,
            value_schema_version=1,
            source_type=AttributeSourceType.ONBOARDING,
            source_reference={
                "onboarding_session_id": declaration_set.onboarding_session_id,
                "onboarding_revision": declaration_set.onboarding_revision,
                "source_schema_version": declaration_set.source_schema_version,
            },
            declared_at=declaration_set.confirmed_at,
            visibility=change.visibility,
            restricted=change.restricted,
            created_by=actor,
        )
        attribute.full_clean()
        attribute.save()
        return attribute

    def _link_onboarding_evidence(self, *, profile, draft, attribute, actor, declaration_set):
        profile.refresh_from_db()
        LinkLearningIdentityEvidenceService(events=self.events).execute(
            profile_id=profile.id,
            profile_version_id=draft.id,
            attribute_id=attribute.id,
            source_domain=EvidenceSourceDomain.SELF_STUDY,
            source_type=EvidenceSourceType.ONBOARDING_CONTEXT,
            source_identifier=_source_identifier(declaration_set),
            relationship=EvidenceRelationship.SUPPORTS,
            actor=actor,
            expected_version=profile.version,
            idempotency_key=f"onboarding-evidence:{declaration_set.onboarding_session_id}:{declaration_set.onboarding_revision}:{attribute.attribute_type}",
        )

    def _publish_events(self, *, receipt, profile, declaration_set, changes):
        payload = self._event_payload(profile, declaration_set, receipt.profile_version, receipt.status)
        payload["synchronization_id"] = str(receipt.id)
        _publish_after_commit(self.events, "learning_identity.declarations.synchronized", payload)
        if receipt.status == DeclarationSynchronizationStatus.BLOCKED:
            _publish_after_commit(self.events, "learning_identity.onboarding_sync.blocked", payload)
        for change in changes:
            if change.change_type not in {
                DeclarationChangeType.ADDED,
                DeclarationChangeType.UPDATED,
                DeclarationChangeType.CLEARED,
                DeclarationChangeType.UNCHANGED,
            }:
                continue
            event_name = {
                DeclarationChangeType.ADDED: "learning_identity.declaration.added",
                DeclarationChangeType.UPDATED: "learning_identity.declaration.updated",
                DeclarationChangeType.CLEARED: "learning_identity.declaration.cleared",
                DeclarationChangeType.UNCHANGED: "learning_identity.declaration.unchanged",
            }[change.change_type]
            _publish_after_commit(
                self.events,
                event_name,
                {
                    **payload,
                    "attribute_type": change.attribute_type,
                    "change_type": change.change_type,
                    "restricted": change.restricted,
                },
            )

    def _event_payload(self, profile, declaration_set, profile_version, status):
        return {
            "profile_id": str(profile.id) if profile else "",
            "profile_version_id": str(profile_version.id) if profile_version else "",
            "learner_id": str(declaration_set.learner_id),
            "tenant_id": str(declaration_set.tenant_id),
            "onboarding_session_id": str(declaration_set.onboarding_session_id),
            "onboarding_revision": declaration_set.onboarding_revision,
            "status": status,
            "aggregate_version": profile.version if profile else 0,
        }


class ClearDeclaredLearningIdentityAttributeService:
    def execute(self, *args, **kwargs):
        raise ValidationError("Explicit clearing is supported through onboarding synchronization only.", code="EXPLICIT_CLEAR_NOT_ALLOWED")
