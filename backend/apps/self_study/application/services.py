from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import InstitutionRole

from ..domain.policy import (
    AcquisitionCandidate,
    PolicyLayer,
    authorize_candidate,
    resolve_effective_policy,
)
from ..models import (
    AutonomousFallbackDecision,
    CurriculumResolutionFailure,
    EffectiveLearningPolicySnapshot,
    IntentStatus,
    LearningMode,
    LearningPolicyRuleSet,
    ResourceAcquisitionDecision,
    SelfStudyIntent,
)


EDITABLE_FIELDS = {
    "goal_statement",
    "target_title",
    "target_outcomes",
    "target_credential",
    "preferred_curriculum_authority",
    "jurisdiction",
    "preferred_language",
    "learner_age_band",
    "accessibility_requirements",
    "desired_depth",
    "pace_preference",
    "time_budget_minutes_per_week",
    "target_completion_date",
    "policy_acknowledged_at",
}


def _has_institutional_authority(actor, tenant_id) -> bool:
    if actor.is_superuser:
        return True
    return actor.institutionmembership_set.filter(
        institution_id=tenant_id,
        is_active=True,
        role__in=[
            InstitutionRole.ADMINISTRATOR,
            InstitutionRole.INSTITUTION_OWNER,
            InstitutionRole.SYSTEM_ADMINISTRATOR,
        ],
    ).exists()


def ensure_access(actor, intent: SelfStudyIntent, *, mutate: bool = False):
    if actor.id == intent.learner_id:
        return
    if _has_institutional_authority(actor, intent.tenant_id):
        return
    raise PermissionDenied("SELF_STUDY_INTENT_ACCESS_DENIED")


def _publish(events: EventPublisher, name: str, intent: SelfStudyIntent, extra=None):
    payload = {
        "intent_id": str(intent.id),
        "learner_id": str(intent.learner_id),
        "tenant_id": str(intent.tenant_id),
        "version": intent.version,
    }
    payload.update(extra or {})
    events.publish(BusinessEvent.create(name, payload=payload))


class CreateSelfStudyIntentService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, actor, learner, tenant, subject, **values):
        if subject.institution_id != tenant.id:
            raise ValidationError("Subject is outside the selected tenant.", code="SELF_STUDY_INTENT_ACCESS_DENIED")
        if actor.id != learner.id and not _has_institutional_authority(actor, tenant.id):
            raise PermissionDenied("INSTITUTIONAL_AUTHORITY_REQUIRED")
        intent = SelfStudyIntent(
            learner=learner,
            tenant=tenant,
            subject=subject,
            created_by=actor,
            **values,
        )
        # Draft persistence validates field structure only. Completeness belongs
        # to DRAFT -> READY and policy validity belongs to READY -> ACTIVE.
        intent.clean_fields()
        intent.save()
        transaction.on_commit(lambda: _publish(self.events, "self_study.intent_created", intent))
        return intent


class UpdateSelfStudyIntentService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, intent_id, actor, expected_version, changes):
        intent = SelfStudyIntent.objects.select_for_update().get(id=intent_id)
        ensure_access(actor, intent, mutate=True)
        if intent.version != expected_version:
            raise ValidationError("Intent version is stale.", code="INTENT_VERSION_CONFLICT")
        if intent.status not in {IntentStatus.DRAFT, IntentStatus.READY}:
            raise ValidationError("Intent is not editable.", code="INTENT_NOT_EDITABLE")
        unknown = set(changes) - EDITABLE_FIELDS
        if unknown:
            raise ValidationError(f"Immutable or unknown fields: {', '.join(sorted(unknown))}.", code="INTENT_NOT_EDITABLE")
        for field, value in changes.items():
            setattr(intent, field, value)
        intent.version += 1
        intent.full_clean()
        intent.save()
        transaction.on_commit(lambda: _publish(self.events, "self_study.intent_updated", intent))
        return intent


class MarkSelfStudyIntentReadyService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, intent_id, actor, expected_version):
        intent = SelfStudyIntent.objects.select_for_update().get(id=intent_id)
        ensure_access(actor, intent, mutate=True)
        if intent.version != expected_version:
            raise ValidationError("Intent version is stale.", code="INTENT_VERSION_CONFLICT")
        intent.mark_ready()
        intent.save(update_fields=["status", "version", "updated_at"])
        transaction.on_commit(lambda: _publish(self.events, "self_study.intent_marked_ready", intent))
        return intent


class ReturnSelfStudyIntentToDraftService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, intent_id, actor, expected_version):
        intent = SelfStudyIntent.objects.select_for_update().get(id=intent_id)
        ensure_access(actor, intent, mutate=True)
        if intent.version != expected_version:
            raise ValidationError("Intent version is stale.", code="INTENT_VERSION_CONFLICT")
        intent.return_to_draft()
        intent.save(update_fields=["status", "version", "updated_at"])
        transaction.on_commit(lambda: _publish(self.events, "self_study.intent_returned_to_draft", intent))
        return intent


def _layer(model: LearningPolicyRuleSet) -> PolicyLayer:
    return PolicyLayer(
        automatic_acquisition_enabled=model.automatic_acquisition_enabled,
        allowed_provider_ids=frozenset(model.allowed_provider_ids),
        allowed_source_categories=frozenset(model.allowed_source_categories),
        allowed_licence_categories=frozenset(model.allowed_licence_categories),
        allowed_mime_types=frozenset(model.allowed_mime_types),
        allowed_languages=frozenset(model.allowed_languages),
        maximum_resource_count=model.maximum_resource_count,
        maximum_single_file_bytes=model.maximum_single_file_bytes,
        maximum_total_bytes=model.maximum_total_bytes,
        maximum_cost=model.maximum_cost,
        cost_currency=model.cost_currency,
        paid_content_allowed=model.paid_content_allowed,
        unknown_licence_allowed=model.unknown_licence_allowed,
        link_only_when_restricted=model.link_only_when_restricted,
        user_approval_threshold=model.user_approval_threshold,
        retention_policy=model.retention_policy,
        external_network_access_enabled=model.external_network_access_enabled,
        autonomous_curriculum_fallback_allowed=model.autonomous_curriculum_fallback_allowed,
    )


class ResolveEffectiveLearningPolicyService:
    def execute(self, intent: SelfStudyIntent):
        policies = list(
            LearningPolicyRuleSet.objects.filter(is_active=True)
            .filter(
                models.Q(authority=LearningPolicyRuleSet.Authority.PLATFORM)
                | models.Q(authority=LearningPolicyRuleSet.Authority.TENANT, tenant=intent.tenant)
                | models.Q(
                    authority=LearningPolicyRuleSet.Authority.LEARNER,
                    tenant=intent.tenant,
                    learner=intent.learner,
                )
            )
            .order_by("authority", "-version")
        )
        selected = {}
        for policy in policies:
            selected.setdefault(policy.authority, policy)
        platform = selected.get(LearningPolicyRuleSet.Authority.PLATFORM)
        if platform is None:
            raise ValidationError("No platform safety policy is configured.", code="EFFECTIVE_POLICY_INVALID")
        ordered = [platform]
        for authority in (LearningPolicyRuleSet.Authority.TENANT, LearningPolicyRuleSet.Authority.LEARNER):
            if authority in selected:
                ordered.append(selected[authority])
        try:
            effective = resolve_effective_policy(*[_layer(item) for item in ordered])
        except ValueError as exc:
            raise ValidationError(str(exc), code="EFFECTIVE_POLICY_INVALID") from exc
        return effective, ordered


class ActivateSelfStudyIntentService:
    def __init__(self, resolver=None, events=None):
        self.resolver = resolver or ResolveEffectiveLearningPolicyService()
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, intent_id, actor, expected_version):
        intent = SelfStudyIntent.objects.select_for_update().get(id=intent_id)
        ensure_access(actor, intent, mutate=True)
        if intent.status == IntentStatus.ACTIVE:
            return intent
        if intent.version != expected_version:
            raise ValidationError("Intent version is stale.", code="INTENT_VERSION_CONFLICT")
        if intent.mode == LearningMode.INSTITUTION_GOVERNED and not _has_institutional_authority(actor, intent.tenant_id):
            raise PermissionDenied("INSTITUTIONAL_AUTHORITY_REQUIRED")
        effective, sources = self.resolver.execute(intent)
        values = asdict(effective)
        for key in (
            "allowed_provider_ids",
            "allowed_source_categories",
            "allowed_licence_categories",
            "allowed_mime_types",
            "allowed_languages",
        ):
            values[key] = sorted(values[key])
        snapshot = EffectiveLearningPolicySnapshot(
            policy_version=intent.version,
            source_policy_ids=[str(item.id) for item in sources],
            **values,
        )
        snapshot.save()
        intent.activate(snapshot)
        intent.save(update_fields=["effective_policy_snapshot", "status", "version", "updated_at"])

        def after_commit():
            _publish(
                self.events,
                "self_study.effective_policy_snapshotted",
                intent,
                {"policy_snapshot_id": str(snapshot.id)},
            )
            _publish(
                self.events,
                "self_study.intent_activated",
                intent,
                {"policy_snapshot_id": str(snapshot.id), "mode": intent.mode},
            )

        transaction.on_commit(after_commit)
        return intent


class CancelSelfStudyIntentService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, intent_id, actor, expected_version):
        intent = SelfStudyIntent.objects.select_for_update().get(id=intent_id)
        ensure_access(actor, intent, mutate=True)
        if intent.status == IntentStatus.CANCELLED:
            return intent
        if intent.version != expected_version:
            raise ValidationError("Intent version is stale.", code="INTENT_VERSION_CONFLICT")
        changed = intent.cancel()
        intent.save(update_fields=["status", "version", "updated_at"])
        if changed:
            transaction.on_commit(lambda: _publish(self.events, "self_study.intent_cancelled", intent))
        return intent


class SupersedeSelfStudyIntentService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, intent_id, actor, expected_version):
        intent = SelfStudyIntent.objects.select_for_update().get(id=intent_id)
        ensure_access(actor, intent, mutate=True)
        if intent.version != expected_version:
            raise ValidationError("Intent version is stale.", code="INTENT_VERSION_CONFLICT")
        intent.supersede()
        intent.save(update_fields=["status", "version", "updated_at"])
        transaction.on_commit(lambda: _publish(self.events, "self_study.intent_superseded", intent))
        return intent


def _snapshot_policy(snapshot: EffectiveLearningPolicySnapshot):
    return resolve_effective_policy(_layer(snapshot))


class AuthorizeResourceAcquisitionService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, intent_id, actor, candidate: AcquisitionCandidate, idempotency_key: str, canonical_uri=""):
        intent = SelfStudyIntent.objects.select_for_update().get(id=intent_id)
        ensure_access(actor, intent, mutate=True)
        if intent.status != IntentStatus.ACTIVE or not intent.effective_policy_snapshot_id:
            raise ValidationError("An active policy snapshot is required.", code="POLICY_SNAPSHOT_REQUIRED")
        try:
            snapshot = EffectiveLearningPolicySnapshot.objects.get(id=intent.effective_policy_snapshot_id)
        except EffectiveLearningPolicySnapshot.DoesNotExist as exc:
            raise ValidationError("The policy snapshot is unavailable.", code="POLICY_SNAPSHOT_REQUIRED") from exc
        key = idempotency_key.strip()
        if not key:
            raise ValidationError("Idempotency key is required.", code="RESOURCE_ACQUISITION_NOT_ALLOWED")
        metadata = asdict(candidate)
        metadata["price"] = str(metadata["price"])
        fingerprint = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
        existing = ResourceAcquisitionDecision.objects.filter(intent=intent, idempotency_key=key).first()
        if existing:
            if existing.candidate_fingerprint != fingerprint:
                raise ValidationError("Idempotency key was used for different metadata.", code="INTENT_VERSION_CONFLICT")
            return existing
        decision, reasons = authorize_candidate(_snapshot_policy(snapshot), candidate)
        record = ResourceAcquisitionDecision.objects.create(
            intent=intent,
            policy_snapshot=snapshot,
            decision=decision,
            reason_codes=list(reasons),
            candidate_metadata=metadata,
            candidate_fingerprint=fingerprint,
            canonical_uri=canonical_uri,
            provider_id=candidate.provider_id,
            decided_by=actor,
            idempotency_key=key,
        )
        event = "self_study.resource_acquisition_authorized" if decision != "REJECTED" else "self_study.resource_acquisition_rejected"
        transaction.on_commit(
            lambda: _publish(
                self.events,
                event,
                intent,
                {"decision_id": str(record.id), "decision": record.decision, "reason_codes": record.reason_codes},
            )
        )
        return record


class AuthorizeAutonomousCurriculumFallbackService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, intent_id, actor, resolution_failure_id, idempotency_key):
        intent = SelfStudyIntent.objects.select_for_update().get(id=intent_id)
        ensure_access(actor, intent, mutate=True)
        if not _has_institutional_authority(actor, intent.tenant_id):
            raise PermissionDenied("INSTITUTIONAL_AUTHORITY_REQUIRED")
        if intent.status != IntentStatus.ACTIVE or not intent.effective_policy_snapshot_id:
            raise ValidationError("An active policy snapshot is required.", code="POLICY_SNAPSHOT_REQUIRED")
        try:
            snapshot = EffectiveLearningPolicySnapshot.objects.get(id=intent.effective_policy_snapshot_id)
        except EffectiveLearningPolicySnapshot.DoesNotExist as exc:
            raise ValidationError("The policy snapshot is unavailable.", code="POLICY_SNAPSHOT_REQUIRED") from exc
        key = idempotency_key.strip()
        if not key:
            raise ValidationError("Idempotency key is required.", code="AUTONOMOUS_FALLBACK_NOT_ALLOWED")
        existing = AutonomousFallbackDecision.objects.filter(intent=intent, idempotency_key=key).first()
        if existing:
            return existing
        failure = None
        reasons = []
        if intent.mode != LearningMode.SELF_STUDY:
            reasons.append("AUTONOMOUS_FALLBACK_NOT_ALLOWED")
        if not snapshot.autonomous_curriculum_fallback_allowed:
            reasons.append("AUTONOMOUS_FALLBACK_NOT_ALLOWED")
        if resolution_failure_id:
            failure = CurriculumResolutionFailure.objects.filter(
                id=resolution_failure_id,
                intent=intent,
                attempt__status="FAILED",
                policy_snapshot_id=intent.effective_policy_snapshot_id,
            ).first()
        if failure is None or not failure.reason_codes:
            reasons.append("CURRICULUM_RESOLUTION_FAILURE_REQUIRED")
        authorized = not reasons
        record = AutonomousFallbackDecision.objects.create(
            intent=intent,
            policy_snapshot=snapshot,
            resolution_failure=failure,
            authorized=authorized,
            reason_codes=list(dict.fromkeys(reasons)),
            decided_by=actor,
            idempotency_key=key,
        )
        event = (
            "self_study.autonomous_fallback_authorized"
            if authorized
            else "self_study.autonomous_fallback_rejected"
        )
        transaction.on_commit(
            lambda: _publish(
                self.events,
                event,
                intent,
                {"decision_id": str(record.id), "authorized": authorized, "reason_codes": record.reason_codes},
            )
        )
        return record
