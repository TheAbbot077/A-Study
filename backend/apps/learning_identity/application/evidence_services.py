from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import User

from ..domain.enums import (
    AttributeClassification,
    AttributeVisibility,
    EvidenceAuthorityClass,
    EvidenceLinkStatus,
    EvidenceRelationship,
    LearningProfileStatus,
    ProvenanceReadinessStatus,
)
from ..domain.models import LearnerLearningProfile, LearningIdentityEvidenceLink, LearningProfileVersion
from ..infrastructure.evidence_resolvers import EvidenceSourceResolverRegistry, build_default_evidence_resolver_registry
from .provenance import apply_provenance_impact, evaluate_profile_version_provenance, relationship_allowed
from .services import _ensure_profile_access, _fingerprint, _get_command, _has_staff_authority, _record_command


def _publish_after_commit(events: EventPublisher, event_name: str, payload: dict[str, Any]) -> None:
    transaction.on_commit(lambda: events.publish(BusinessEvent.create(event_name, payload=payload)))


def _payload(link: LearningIdentityEvidenceLink, profile: LearnerLearningProfile, reason_code: str = "") -> dict[str, Any]:
    payload = {
        "profile_id": str(profile.id),
        "profile_version_id": str(link.attribute.profile_version_id),
        "attribute_id": str(link.attribute_id),
        "evidence_link_id": str(link.id),
        "source_domain": link.source_domain,
        "source_type": link.source_type,
        "relationship": link.relationship,
        "authority_class": link.authority_class,
        "status": link.status,
        "aggregate_version": profile.version,
    }
    if reason_code:
        payload["reason_code"] = reason_code
    return payload


def _ensure_version(profile: LearnerLearningProfile, expected_version: int):
    if profile.version != expected_version:
        raise ValidationError("Learning profile version conflict.", code="LEARNING_PROFILE_VERSION_CONFLICT")


def _can_control_link(actor: User, link: LearningIdentityEvidenceLink) -> bool:
    profile = link.attribute.profile_version.profile
    if _has_staff_authority(actor=actor, tenant_id=profile.tenant_id):
        return True
    return (
        actor.id == profile.learner_id
        and link.authority_class == EvidenceAuthorityClass.DECLARATIVE
        and link.source_type in {"LEARNER_DECLARATION", "ONBOARDING_CONTEXT"}
    )


class LinkLearningIdentityEvidenceService:
    def __init__(self, *, resolver_registry: EvidenceSourceResolverRegistry | None = None, events: EventPublisher | None = None):
        self.resolver_registry = resolver_registry or build_default_evidence_resolver_registry()
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(
        self,
        *,
        profile_id,
        profile_version_id,
        attribute_id,
        source_domain: str,
        source_type: str,
        source_identifier: str,
        relationship: str,
        actor: User,
        expected_version: int,
        idempotency_key: str = "",
        source_revision: str = "",
        weight=1,
        confidence_contribution=None,
        valid_from=None,
        valid_until=None,
    ):
        request_payload = {
            "profile_id": str(profile_id),
            "profile_version_id": str(profile_version_id),
            "attribute_id": str(attribute_id),
            "source_domain": source_domain,
            "source_type": source_type,
            "source_identifier": str(source_identifier),
            "relationship": relationship,
            "actor_id": str(actor.id),
            "expected_version": expected_version,
            "source_revision": source_revision,
            "weight": str(weight),
            "confidence_contribution": str(confidence_contribution),
            "valid_from": valid_from,
            "valid_until": valid_until,
        }
        fp = _fingerprint(request_payload)
        if record := _get_command("learning_identity.evidence.link", idempotency_key, fp):
            return LearningIdentityEvidenceLink.objects.get(id=record.result_id)

        profile = LearnerLearningProfile.objects.select_for_update().get(id=profile_id)
        _ensure_profile_access(actor=actor, profile=profile, mutate=True)
        _ensure_version(profile, expected_version)
        version = LearningProfileVersion.objects.select_for_update().get(id=profile_version_id, profile=profile)
        version.ensure_draft()
        attribute = version.attributes.select_for_update().get(id=attribute_id)
        resolution = self.resolver_registry.resolve(
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=str(source_identifier),
            learner_id=profile.learner_id,
            tenant_id=profile.tenant_id,
        )
        if not resolution.exists:
            raise ValidationError("Evidence source was not found.", code=resolution.reason_code or "SOURCE_NOT_FOUND")
        if str(resolution.tenant_id) != str(profile.tenant_id):
            raise PermissionDenied("SOURCE_TENANT_MISMATCH")
        if str(resolution.learner_id) != str(profile.learner_id):
            raise PermissionDenied("SOURCE_LEARNER_MISMATCH")
        if resolution.is_deleted:
            raise ValidationError("Evidence source was deleted.", code="SOURCE_NOT_FOUND")
        if resolution.is_revoked:
            raise ValidationError("Evidence source was revoked.", code="SOURCE_REVOKED")
        if not resolution.is_active:
            raise ValidationError("Evidence source is inactive.", code="SOURCE_INACTIVE")
        if not relationship_allowed(relationship=relationship, authority_class=resolution.authority_class, classification=attribute.classification):
            raise ValidationError("Evidence relationship is not compatible with source authority.", code="SOURCE_RELATIONSHIP_INVALID")
        if attribute.classification == AttributeClassification.VERIFIED and relationship == EvidenceRelationship.CONFIRMS and not resolution.is_authoritative:
            raise ValidationError("Source authority is insufficient for verified attributes.", code="SOURCE_AUTHORITY_INSUFFICIENT")
        if relationship == EvidenceRelationship.CONFIRMS and resolution.authority_class == EvidenceAuthorityClass.DECLARATIVE:
            raise ValidationError("A declaration cannot confirm itself.", code="SOURCE_AUTHORITY_INSUFFICIENT")

        starting_profile_version = profile.version
        link = LearningIdentityEvidenceLink(
            attribute=attribute,
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=str(source_identifier),
            source_revision=source_revision or resolution.source_revision,
            relationship=relationship,
            authority_class=resolution.authority_class,
            status=EvidenceLinkStatus.ACTIVE,
            source_observed_at=resolution.observed_at,
            valid_from=valid_from or resolution.valid_from,
            valid_until=valid_until or resolution.valid_until,
            weight=weight,
            confidence_contribution=confidence_contribution,
            safe_summary=resolution.safe_summary[:240],
            summary_visibility=resolution.summary_visibility,
            linked_by=actor,
        )
        link.full_clean()
        link.save()
        impact_codes = apply_provenance_impact(profile, attribute, link)
        if impact_codes:
            link.reason_codes = impact_codes
            link.review_required = True
            link.save(update_fields=["reason_codes", "review_required", "updated_at"])
            attribute.save(update_fields=["review_required"])
            if profile.status == LearningProfileStatus.NEEDS_REVIEW:
                profile.save(update_fields=["status", "version", "updated_at"])
            elif profile.version == starting_profile_version:
                profile.version += 1
                profile.save(update_fields=["version", "updated_at"])
        else:
            profile.version += 1
            profile.save(update_fields=["version", "updated_at"])
        _record_command("learning_identity.evidence.link", idempotency_key, fp, link)
        _publish_after_commit(self.events, "learning_identity.evidence.linked", _payload(link, profile))
        if relationship == EvidenceRelationship.CONTRADICTS:
            _publish_after_commit(self.events, "learning_identity.attribute.contradicted", _payload(link, profile, "CONTRADICTORY_EVIDENCE"))
            _publish_after_commit(self.events, "learning_identity.profile.provenance_review_required", _payload(link, profile, "CONTRADICTORY_EVIDENCE"))
        return link


class EvidenceLifecycleService:
    event_name = ""
    command_scope = ""

    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    def _load(self, evidence_link_id, actor: User, expected_version: int):
        link = LearningIdentityEvidenceLink.objects.select_for_update().select_related("attribute__profile_version__profile").get(id=evidence_link_id)
        profile = LearnerLearningProfile.objects.select_for_update().get(id=link.attribute.profile_version.profile_id)
        _ensure_version(profile, expected_version)
        if not _can_control_link(actor, link):
            raise PermissionDenied("LEARNING_IDENTITY_EVIDENCE_ACCESS_DENIED")
        return link, profile


class WithdrawLearningIdentityEvidenceService(EvidenceLifecycleService):
    event_name = "learning_identity.evidence.withdrawn"
    command_scope = "learning_identity.evidence.withdraw"

    @transaction.atomic
    def execute(self, *, evidence_link_id, actor: User, reason_code: str, expected_version: int, idempotency_key: str = ""):
        fp = _fingerprint({"evidence_link_id": str(evidence_link_id), "actor_id": str(actor.id), "reason_code": reason_code, "expected_version": expected_version})
        if record := _get_command(self.command_scope, idempotency_key, fp):
            return LearningIdentityEvidenceLink.objects.get(id=record.result_id)
        link, profile = self._load(evidence_link_id, actor, expected_version)
        starting_profile_version = profile.version
        link.withdraw(actor=actor, reason_code=reason_code)
        link.save(update_fields=["status", "withdrawn_by", "withdrawn_at", "withdrawal_reason_code", "updated_at"])
        codes = apply_provenance_impact(profile, link.attribute, link)
        link.attribute.save(update_fields=["review_required"])
        if profile.version == starting_profile_version:
            profile.version += 1
        profile.save(update_fields=["status", "version", "updated_at"])
        _record_command(self.command_scope, idempotency_key, fp, link)
        _publish_after_commit(self.events, self.event_name, _payload(link, profile, reason_code))
        if codes:
            _publish_after_commit(self.events, "learning_identity.profile.provenance_review_required", _payload(link, profile, codes[0]))
        return link


class InvalidateLearningIdentityEvidenceService(EvidenceLifecycleService):
    event_name = "learning_identity.evidence.invalidated"
    command_scope = "learning_identity.evidence.invalidate"

    @transaction.atomic
    def execute(self, *, evidence_link_id, actor: User, reason_code: str, expected_version: int, idempotency_key: str = ""):
        fp = _fingerprint({"evidence_link_id": str(evidence_link_id), "actor_id": str(actor.id), "reason_code": reason_code, "expected_version": expected_version})
        if record := _get_command(self.command_scope, idempotency_key, fp):
            return LearningIdentityEvidenceLink.objects.get(id=record.result_id)
        link, profile = self._load(evidence_link_id, actor, expected_version)
        if not _has_staff_authority(actor=actor, tenant_id=profile.tenant_id):
            raise PermissionDenied("LEARNING_IDENTITY_INVALIDATE_DENIED")
        starting_profile_version = profile.version
        link.invalidate(actor=actor, reason_code=reason_code)
        link.save(update_fields=["status", "invalidated_by", "invalidated_at", "invalidation_reason_code", "updated_at"])
        codes = apply_provenance_impact(profile, link.attribute, link)
        link.attribute.save(update_fields=["review_required"])
        if profile.version == starting_profile_version:
            profile.version += 1
        profile.save(update_fields=["status", "version", "updated_at"])
        _record_command(self.command_scope, idempotency_key, fp, link)
        _publish_after_commit(self.events, self.event_name, _payload(link, profile, reason_code))
        if codes:
            _publish_after_commit(self.events, "learning_identity.profile.provenance_review_required", _payload(link, profile, codes[0]))
        return link


class MarkLearningIdentityEvidenceStaleService(EvidenceLifecycleService):
    event_name = "learning_identity.evidence.marked_stale"
    command_scope = "learning_identity.evidence.mark_stale"

    @transaction.atomic
    def execute(self, *, evidence_link_id, actor: User, reason_code: str, expected_version: int, idempotency_key: str = ""):
        fp = _fingerprint({"evidence_link_id": str(evidence_link_id), "actor_id": str(actor.id), "reason_code": reason_code, "expected_version": expected_version})
        if record := _get_command(self.command_scope, idempotency_key, fp):
            return LearningIdentityEvidenceLink.objects.get(id=record.result_id)
        link, profile = self._load(evidence_link_id, actor, expected_version)
        starting_profile_version = profile.version
        link.mark_stale(reason_code=reason_code)
        link.save(update_fields=["status", "reason_codes", "updated_at"])
        codes = apply_provenance_impact(profile, link.attribute, link)
        link.attribute.save(update_fields=["review_required"])
        if profile.version == starting_profile_version:
            profile.version += 1
        profile.save(update_fields=["status", "version", "updated_at"])
        _record_command(self.command_scope, idempotency_key, fp, link)
        _publish_after_commit(self.events, self.event_name, _payload(link, profile, reason_code))
        if codes:
            _publish_after_commit(self.events, "learning_identity.profile.provenance_review_required", _payload(link, profile, codes[0]))
        return link


class SupersedeLearningIdentityEvidenceService:
    def __init__(self, *, resolver_registry: EvidenceSourceResolverRegistry | None = None, events: EventPublisher | None = None):
        self.resolver_registry = resolver_registry or build_default_evidence_resolver_registry()
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, prior_evidence_link_id, source_identifier: str, actor: User, expected_version: int, idempotency_key: str = "", source_revision: str = ""):
        prior = LearningIdentityEvidenceLink.objects.select_for_update().select_related("attribute__profile_version__profile").get(id=prior_evidence_link_id)
        profile = LearnerLearningProfile.objects.select_for_update().get(id=prior.attribute.profile_version.profile_id)
        fp = _fingerprint({"prior": str(prior_evidence_link_id), "source_identifier": source_identifier, "actor_id": str(actor.id), "expected_version": expected_version, "source_revision": source_revision})
        if record := _get_command("learning_identity.evidence.supersede", idempotency_key, fp):
            return LearningIdentityEvidenceLink.objects.get(id=record.result_id)
        _ensure_profile_access(actor=actor, profile=profile, mutate=True)
        _ensure_version(profile, expected_version)
        if prior.is_terminal:
            raise ValidationError("Terminal evidence cannot be superseded.", code="EVIDENCE_TERMINAL")
        service = LinkLearningIdentityEvidenceService(resolver_registry=self.resolver_registry, events=self.events)
        successor = service.execute(
            profile_id=profile.id,
            profile_version_id=prior.attribute.profile_version_id,
            attribute_id=prior.attribute_id,
            source_domain=prior.source_domain,
            source_type=prior.source_type,
            source_identifier=source_identifier,
            source_revision=source_revision,
            relationship=prior.relationship,
            actor=actor,
            expected_version=profile.version,
        )
        profile.refresh_from_db()
        prior.mark_superseded(successor=successor)
        prior.save(update_fields=["status", "superseded_by_link", "superseded_at", "updated_at"])
        profile.version += 1
        profile.save(update_fields=["version", "updated_at"])
        _record_command("learning_identity.evidence.supersede", idempotency_key, fp, successor)
        _publish_after_commit(self.events, "learning_identity.evidence.superseded", _payload(prior, profile, "UNRESOLVED_SUPERSESSION"))
        return successor


class EvaluateProfileVersionProvenanceService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    def execute(self, *, profile_version_id, actor: User):
        version = LearningProfileVersion.objects.select_related("profile").prefetch_related("attributes__evidence_links").get(id=profile_version_id)
        _ensure_profile_access(actor=actor, profile=version.profile, mutate=False)
        readiness = evaluate_profile_version_provenance(version)
        transaction.on_commit(
            lambda: self.events.publish(
                BusinessEvent.create(
                    "learning_identity.profile_version.provenance_evaluated",
                    payload={
                        "profile_id": str(version.profile_id),
                        "profile_version_id": str(version.id),
                        "status": readiness.status,
                        "blocking_codes": readiness.blocking_codes,
                        "review_codes": readiness.review_codes,
                    },
                )
            )
        )
        return readiness
