from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import User

from ..domain.enums import (
    AttributeClassification,
    AttributeSourceType,
    EvidenceAuthorityClass,
    EvidenceSourceDomain,
    EvidenceSourceType,
    LearnerPreferenceStatus,
    LearningProfileStatus,
    LearningIdentityReviewAction,
    LearningIdentityReviewStatus,
    LearningObservationStatus,
    LearningObservationType,
    ObservationSynchronizationResultCode,
    ObservationSynchronizationStatus,
)
from ..domain.models import (
    LearnerLearningProfile,
    LearnerPreferenceSelection,
    LearningIdentityAttribute,
    LearningIdentityCorrectionRequest,
    LearningIdentityObservation,
    LearningIdentityObservationSynchronization,
    LearningProfileVersion,
)
from ..domain.preferences import PREFERENCE_REGISTRY, validate_preference_value
from .ports import LearningIdentityObservationSourceResolver, ObservationSourceEnvelope
from .services import (
    _ensure_actor_can_manage,
    _ensure_profile_access,
    _event_payload,
    _fingerprint,
    _get_command,
    _record_command,
    _publish_after_commit,
)


PROHIBITED_OBSERVATION_TERMS = {
    "mastered",
    "weak",
    "low ability",
    "gifted",
    "lazy",
    "visual learner",
    "auditory learner",
    "dyslexic",
    "anxious",
    "unmotivated",
    "personality",
    "transcript",
}


@dataclass(frozen=True)
class ObservationRule:
    source_domain: str
    source_type: str
    observation_type: str
    authority_class: str
    learner_summary_eligible: bool
    mentor_context_eligible: bool
    title: str
    prohibited_payload_fields: tuple[str, ...] = ("score", "ability", "mastery", "transcript", "raw_text", "diagnostic_estimate")


OBSERVATION_REGISTRY: dict[tuple[str, str], ObservationRule] = {
    (EvidenceSourceDomain.SELF_STUDY, EvidenceSourceType.DIAGNOSTIC_ATTEMPT): ObservationRule(
        source_domain=EvidenceSourceDomain.SELF_STUDY,
        source_type=EvidenceSourceType.DIAGNOSTIC_ATTEMPT,
        observation_type=LearningObservationType.DIAGNOSTIC_COMPLETED,
        authority_class=EvidenceAuthorityClass.DIAGNOSTIC,
        learner_summary_eligible=True,
        mentor_context_eligible=True,
        title="Diagnostic completed",
    ),
    (EvidenceSourceDomain.SELF_STUDY, EvidenceSourceType.LEARNING_SESSION): ObservationRule(
        source_domain=EvidenceSourceDomain.SELF_STUDY,
        source_type=EvidenceSourceType.LEARNING_SESSION,
        observation_type=LearningObservationType.LEARNING_SESSION_COMPLETED,
        authority_class=EvidenceAuthorityClass.OBSERVATIONAL,
        learner_summary_eligible=True,
        mentor_context_eligible=True,
        title="Learning session completed",
    ),
    (EvidenceSourceDomain.LEARNING, EvidenceSourceType.LEARNING_SESSION): ObservationRule(
        source_domain=EvidenceSourceDomain.LEARNING,
        source_type=EvidenceSourceType.LEARNING_SESSION,
        observation_type=LearningObservationType.LEARNING_SESSION_COMPLETED,
        authority_class=EvidenceAuthorityClass.OBSERVATIONAL,
        learner_summary_eligible=True,
        mentor_context_eligible=True,
        title="Learning session completed",
    ),
}


def _safe_json_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _profile_for_actor(*, profile_id, actor: User, lock: bool = False) -> LearnerLearningProfile:
    query = LearnerLearningProfile.objects.select_related("tenant", "learner")
    if not lock:
        query = query.select_related("current_version")
    if lock:
        query = query.select_for_update()
    profile = query.get(id=profile_id)
    _ensure_profile_access(actor=actor, profile=profile, mutate=lock)
    return profile


def _current_profile_for_learner(*, tenant_id, learner_id, actor: User, lock: bool = False) -> LearnerLearningProfile:
    query = LearnerLearningProfile.objects.select_related("tenant", "learner")
    if not lock:
        query = query.select_related("current_version")
    if lock:
        query = query.select_for_update()
    profile = query.exclude(status="ARCHIVED").get(tenant_id=tenant_id, learner_id=learner_id)
    _ensure_profile_access(actor=actor, profile=profile, mutate=lock)
    return profile


def _validate_safe_payload(payload: dict[str, Any], *, prohibited_fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Observation payload must be controlled.", code="OBSERVATION_PAYLOAD_INVALID")
    lowered_keys = {str(key).lower() for key in payload.keys()}
    if lowered_keys.intersection({field.lower() for field in prohibited_fields}):
        raise ValidationError("Observation payload contains prohibited fields.", code="OBSERVATION_PAYLOAD_PROHIBITED")
    as_text = json.dumps(payload, sort_keys=True, default=str).lower()
    if any(term in as_text for term in PROHIBITED_OBSERVATION_TERMS):
        raise ValidationError("Observation payload uses prohibited learner-trait language.", code="OBSERVATION_PAYLOAD_UNSAFE")
    return payload


class SynchronizeLearningObservationService:
    def __init__(self, *, resolver: LearningIdentityObservationSourceResolver | None = None, events: EventPublisher | None = None):
        self.resolver = resolver
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(
        self,
        *,
        source_domain: str,
        source_type: str,
        source_identifier: str,
        tenant_id,
        learner_id,
        actor: User,
        idempotency_key: str = "",
    ) -> LearningIdentityObservationSynchronization:
        rule = OBSERVATION_REGISTRY.get((source_domain, source_type))
        base_payload = {
            "source_domain": source_domain,
            "source_type": source_type,
            "source_identifier": str(source_identifier),
            "tenant_id": str(tenant_id),
            "learner_id": str(learner_id),
        }
        fp = _fingerprint(base_payload)
        if record := _get_command("learning_identity.observation.sync", idempotency_key, fp):
            return LearningIdentityObservationSynchronization.objects.get(id=record.result_id)
        if rule is None:
            receipt = self._receipt(
                tenant_id=tenant_id,
                learner_id=learner_id,
                payload=base_payload,
                status=ObservationSynchronizationStatus.BLOCKED,
                result_code=ObservationSynchronizationResultCode.UNSUPPORTED_SOURCE_TYPE,
                reason_codes=["UNSUPPORTED_SOURCE_TYPE"],
                idempotency_key=idempotency_key,
            )
            _record_command("learning_identity.observation.sync", idempotency_key, fp, receipt)
            _publish_after_commit(self.events, "learning_identity.observation.rejected", self._receipt_payload(receipt))
            return receipt
        if self.resolver is None:
            raise ValidationError("Observation source resolver is required.", code="OBSERVATION_SOURCE_RESOLVER_REQUIRED")
        envelope = self.resolver.resolve(
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=str(source_identifier),
            learner_id=learner_id,
            tenant_id=tenant_id,
        )
        if not envelope.exists:
            receipt = self._receipt(
                tenant_id=tenant_id,
                learner_id=learner_id,
                payload=base_payload,
                status=ObservationSynchronizationStatus.BLOCKED,
                result_code=ObservationSynchronizationResultCode.SOURCE_UNAVAILABLE,
                reason_codes=[envelope.reason_code or "SOURCE_UNAVAILABLE"],
                idempotency_key=idempotency_key,
            )
            _record_command("learning_identity.observation.sync", idempotency_key, fp, receipt)
            _publish_after_commit(self.events, "learning_identity.observation.rejected", self._receipt_payload(receipt))
            return receipt
        if str(envelope.tenant_id) != str(tenant_id) or str(envelope.learner_id) != str(learner_id):
            raise PermissionDenied("LEARNING_IDENTITY_TENANT_MISMATCH")
        profile = _current_profile_for_learner(tenant_id=tenant_id, learner_id=learner_id, actor=actor, lock=True)
        payload = _validate_safe_payload(envelope.controlled_payload or {}, prohibited_fields=rule.prohibited_payload_fields)
        full_payload = {
            **base_payload,
            "source_revision": envelope.source_revision,
            "observation_type": envelope.observation_type,
            "payload": payload,
        }
        payload_fp = _safe_json_fingerprint(full_payload)
        existing = LearningIdentityObservation.objects.filter(
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=str(source_identifier),
            source_revision=envelope.source_revision,
        ).first()
        if existing:
            receipt = self._receipt(
                tenant_id=tenant_id,
                learner_id=learner_id,
                profile=profile,
                observation=existing,
                payload=full_payload,
                status=ObservationSynchronizationStatus.UNCHANGED,
                result_code=ObservationSynchronizationResultCode.DUPLICATE,
                idempotency_key=idempotency_key,
            )
            _record_command("learning_identity.observation.sync", idempotency_key, fp, receipt)
            _publish_after_commit(self.events, "learning_identity.observation.unchanged", self._receipt_payload(receipt))
            return receipt
        prior_current = (
            LearningIdentityObservation.objects.select_for_update()
            .filter(
                source_domain=source_domain,
                source_type=source_type,
                source_identifier=str(source_identifier),
                status=LearningObservationStatus.ACTIVE,
            )
            .exclude(source_revision=envelope.source_revision)
            .first()
        )
        observation = LearningIdentityObservation.objects.create(
            profile=profile,
            tenant_id=tenant_id,
            learner_id=learner_id,
            observation_type=rule.observation_type,
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=str(source_identifier),
            source_revision=envelope.source_revision,
            semantic_key=f"{rule.observation_type}:{source_domain}:{source_type}:{source_identifier}",
            authority_class=rule.authority_class,
            occurred_at=envelope.occurred_at or timezone.now(),
            learner_visible=rule.learner_summary_eligible,
            mentor_context_eligible=rule.mentor_context_eligible,
            safe_title=envelope.learner_safe_title or rule.title,
            safe_summary=envelope.learner_safe_summary[:280],
            controlled_payload=payload,
        )
        if prior_current:
            prior_current.status = LearningObservationStatus.SUPERSEDED
            prior_current.superseded_by = observation
            prior_current.mentor_context_eligible = False
            prior_current.save(update_fields=["status", "superseded_by", "mentor_context_eligible", "updated_at"])
        receipt = self._receipt(
            tenant_id=tenant_id,
            learner_id=learner_id,
            profile=profile,
            observation=observation,
            payload={**full_payload, "fingerprint": payload_fp},
            status=ObservationSynchronizationStatus.APPLIED,
            result_code=ObservationSynchronizationResultCode.CREATED,
            idempotency_key=idempotency_key,
            applied=True,
        )
        _record_command("learning_identity.observation.sync", idempotency_key, fp, receipt)
        _publish_after_commit(self.events, "learning_identity.observation.synchronized", self._receipt_payload(receipt))
        return receipt

    def _receipt(self, *, tenant_id, learner_id, payload: dict, status: str, result_code: str, reason_codes=None, idempotency_key="", profile=None, observation=None, applied=False):
        now = timezone.now()
        return LearningIdentityObservationSynchronization.objects.create(
            profile=profile,
            observation=observation,
            tenant_id=tenant_id,
            learner_id=learner_id,
            source_domain=payload["source_domain"],
            source_type=payload["source_type"],
            source_identifier=payload["source_identifier"],
            source_revision=payload.get("source_revision", ""),
            payload_fingerprint=_safe_json_fingerprint(payload),
            status=status,
            result_code=result_code,
            reason_codes=reason_codes or [],
            idempotency_key=idempotency_key,
            applied_at=now if applied else None,
            blocked_at=now if status == ObservationSynchronizationStatus.BLOCKED else None,
            failed_at=now if status == ObservationSynchronizationStatus.FAILED else None,
        )

    def _receipt_payload(self, receipt: LearningIdentityObservationSynchronization) -> dict[str, Any]:
        return {
            "receipt_id": str(receipt.id),
            "observation_id": str(receipt.observation_id) if receipt.observation_id else "",
            "profile_id": str(receipt.profile_id) if receipt.profile_id else "",
            "tenant_id": str(receipt.tenant_id),
            "learner_id": str(receipt.learner_id),
            "source_domain": receipt.source_domain,
            "source_type": receipt.source_type,
            "result_code": receipt.result_code,
            "status": receipt.status,
        }


class SetLearnerPreferenceService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, profile_id, actor: User, expected_profile_version: int, preference_key: str, value: Any, idempotency_key: str = ""):
        payload = {
            "profile_id": str(profile_id),
            "actor_id": str(actor.id),
            "expected_profile_version": expected_profile_version,
            "preference_key": preference_key,
            "value": value,
        }
        fp = _fingerprint(payload)
        if record := _get_command("learning_identity.preference.set", idempotency_key, fp):
            return LearnerPreferenceSelection.objects.get(id=record.result_id)
        definition = PREFERENCE_REGISTRY.get(preference_key)
        if definition is None:
            raise ValidationError("Unsupported learner preference.", code="UNSUPPORTED_PREFERENCE")
        value = validate_preference_value(preference_key, value)
        profile = _profile_for_actor(profile_id=profile_id, actor=actor, lock=True)
        if profile.version != expected_profile_version:
            raise ValidationError("Learning profile version conflict.", code="LEARNING_PROFILE_VERSION_CONFLICT")
        current = LearnerPreferenceSelection.objects.filter(
            profile=profile,
            preference_key=preference_key,
            status=LearnerPreferenceStatus.ACTIVE,
        ).first()
        if current and current.value == value:
            _record_command("learning_identity.preference.set", idempotency_key, fp, current)
            return current
        if current:
            current.status = LearnerPreferenceStatus.SUPERSEDED
            current.save(update_fields=["status"])
        preference = LearnerPreferenceSelection.objects.create(
            profile=profile,
            tenant=profile.tenant,
            learner=profile.learner,
            preference_key=preference_key,
            value=value,
            explicit=True,
            mentor_context_eligible=definition.mentor_context_eligible,
            teaching_context_eligible=definition.teaching_context_eligible,
            version=(current.version + 1) if current else 1,
            supersedes=current,
            created_by=actor,
        )
        profile.version += 1
        profile.save(update_fields=["version", "updated_at"])
        _record_command("learning_identity.preference.set", idempotency_key, fp, preference)
        _publish_after_commit(self.events, "learning_identity.preference.updated" if current else "learning_identity.preference.selected", _event_payload(profile, preference_id=str(preference.id), preference_key=preference_key))
        return preference


class WithdrawLearnerPreferenceService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, profile_id, actor: User, expected_profile_version: int, preference_key: str, idempotency_key: str = ""):
        payload = {"profile_id": str(profile_id), "actor_id": str(actor.id), "expected_profile_version": expected_profile_version, "preference_key": preference_key}
        fp = _fingerprint(payload)
        if record := _get_command("learning_identity.preference.withdraw", idempotency_key, fp):
            return LearnerPreferenceSelection.objects.get(id=record.result_id)
        profile = _profile_for_actor(profile_id=profile_id, actor=actor, lock=True)
        if profile.version != expected_profile_version:
            raise ValidationError("Learning profile version conflict.", code="LEARNING_PROFILE_VERSION_CONFLICT")
        preference = LearnerPreferenceSelection.objects.select_for_update().get(
            profile=profile,
            preference_key=preference_key,
            status=LearnerPreferenceStatus.ACTIVE,
        )
        preference.withdraw()
        preference.save(update_fields=["status", "withdrawn_at", "withdrawal_reason_code", "mentor_context_eligible", "teaching_context_eligible"])
        profile.version += 1
        profile.save(update_fields=["version", "updated_at"])
        _record_command("learning_identity.preference.withdraw", idempotency_key, fp, preference)
        _publish_after_commit(self.events, "learning_identity.preference.withdrawn", _event_payload(profile, preference_id=str(preference.id), preference_key=preference_key))
        return preference


class ContestLearningObservationService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, observation_id, actor: User, reason_code: str, learner_note: str = "", idempotency_key: str = ""):
        payload = {"observation_id": str(observation_id), "actor_id": str(actor.id), "reason_code": reason_code, "learner_note": learner_note[:500]}
        fp = _fingerprint(payload)
        if record := _get_command("learning_identity.observation.contest", idempotency_key, fp):
            return LearningIdentityCorrectionRequest.objects.get(id=record.result_id)
        observation = LearningIdentityObservation.objects.select_for_update().select_related("profile").get(id=observation_id)
        _ensure_profile_access(actor=actor, profile=observation.profile, mutate=True)
        observation.contest()
        observation.mentor_context_eligible = False
        observation.save(update_fields=["status", "contested_at", "mentor_context_eligible", "updated_at"])
        correction = LearningIdentityCorrectionRequest.objects.create(
            profile=observation.profile,
            tenant=observation.tenant,
            learner=observation.learner,
            target_observation=observation,
            action=LearningIdentityReviewAction.CONTEST_OBSERVATION,
            reason_code=reason_code[:64],
            learner_note=learner_note[:500],
            idempotency_key=idempotency_key,
        )
        _record_command("learning_identity.observation.contest", idempotency_key, fp, correction)
        _publish_after_commit(self.events, "learning_identity.observation.contested", _event_payload(observation.profile, observation_id=str(observation.id), correction_request_id=str(correction.id)))
        return correction


class WithdrawDeclaredAttributeService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, attribute_id, actor: User, expected_profile_version: int, reason_code: str, idempotency_key: str = ""):
        payload = {"attribute_id": str(attribute_id), "actor_id": str(actor.id), "expected_profile_version": expected_profile_version, "reason_code": reason_code}
        fp = _fingerprint(payload)
        if record := _get_command("learning_identity.declaration.withdraw", idempotency_key, fp):
            return LearningIdentityCorrectionRequest.objects.get(id=record.result_id)
        attribute = LearningIdentityAttribute.objects.select_related("profile_version__profile").get(id=attribute_id)
        profile = LearnerLearningProfile.objects.select_for_update().get(id=attribute.profile_version.profile_id)
        _ensure_profile_access(actor=actor, profile=profile, mutate=True)
        if profile.version != expected_profile_version:
            raise ValidationError("Learning profile version conflict.", code="LEARNING_PROFILE_VERSION_CONFLICT")
        if attribute.classification != AttributeClassification.DECLARED:
            raise ValidationError("Only declared attributes can be withdrawn by the learner.", code="ATTRIBUTE_NOT_LEARNER_EDITABLE")
        if LearningProfileVersion.objects.filter(profile=profile, status="DRAFT").exists():
            raise ValidationError("A draft profile version already exists.", code="LEARNING_PROFILE_DRAFT_EXISTS")
        draft = LearningProfileVersion.objects.create(
            profile=profile,
            version_number=(LearningProfileVersion.objects.filter(profile=profile).order_by("-version_number").values_list("version_number", flat=True).first() or 0) + 1,
            created_by=actor,
        )
        if profile.current_version_id:
            for current_attribute in profile.current_version.attributes.exclude(id=attribute.id):
                LearningIdentityAttribute.objects.create(
                    profile_version=draft,
                    attribute_type=current_attribute.attribute_type,
                    classification=current_attribute.classification,
                    value=current_attribute.value,
                    value_schema_version=current_attribute.value_schema_version,
                    confidence=current_attribute.confidence,
                    source_type=current_attribute.source_type,
                    source_reference=current_attribute.source_reference,
                    declared_at=current_attribute.declared_at,
                    valid_from=current_attribute.valid_from,
                    valid_until=current_attribute.valid_until,
                    visibility=current_attribute.visibility,
                    review_required=current_attribute.review_required,
                    restricted=current_attribute.restricted,
                    created_by=actor,
                )
        previous = profile.current_version
        draft.publish(actor=actor, supersedes=previous)
        draft.full_clean()
        draft.save(update_fields=["status", "published_by", "published_at", "supersedes_version"])
        if previous:
            previous.mark_superseded()
            previous.save(update_fields=["status", "superseded_at"])
        correction = LearningIdentityCorrectionRequest.objects.create(
            profile=profile,
            tenant=profile.tenant,
            learner=profile.learner,
            target_attribute=attribute,
            action=LearningIdentityReviewAction.WITHDRAW_DECLARATION,
            reason_code=reason_code[:64],
            status=LearningIdentityReviewStatus.RESOLVED,
            resolved_at=timezone.now(),
            resolved_by=actor,
            resolution_code="DECLARATION_WITHDRAWN",
            resulting_profile_version=draft,
            idempotency_key=idempotency_key,
        )
        profile.current_version = draft
        if profile.status != LearningProfileStatus.RESTRICTED:
            profile.status = LearningProfileStatus.ACTIVE
        profile.version += 1
        profile.save(update_fields=["current_version", "status", "version", "updated_at"])
        _record_command("learning_identity.declaration.withdraw", idempotency_key, fp, correction)
        if previous:
            _publish_after_commit(self.events, "learning_identity.profile_version.superseded", _event_payload(profile, profile_version_id=str(previous.id), superseded_by_version_id=str(draft.id)))
        _publish_after_commit(self.events, "learning_identity.profile_version.published", _event_payload(profile, profile_version_id=str(draft.id), version_number=draft.version_number))
        _publish_after_commit(self.events, "learning_identity.declaration.withdrawn", _event_payload(profile, attribute_id=str(attribute.id), correction_request_id=str(correction.id)))
        return correction
