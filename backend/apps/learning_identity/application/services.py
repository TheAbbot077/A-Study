from __future__ import annotations

import hashlib
import json
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import InstitutionMembership, InstitutionRole, User

from ..domain.enums import (
    AttributeClassification,
    AttributeSourceType,
    AttributeVisibility,
    LearningProfileStatus,
    ProfileVersionStatus,
    ProvenanceReadinessStatus,
)
from ..domain.models import (
    LearnerLearningProfile,
    LearningIdentityAttribute,
    LearningIdentityCommandRecord,
    LearningProfileVersion,
)
from ..domain.validators import validate_attribute_value
from .provenance import evaluate_profile_version_provenance


STAFF_ROLES = {
    InstitutionRole.ADMINISTRATOR,
    InstitutionRole.INSTITUTION_OWNER,
    InstitutionRole.SYSTEM_ADMINISTRATOR,
    InstitutionRole.TEACHER,
    InstitutionRole.REVIEWER,
}


def _fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _membership_exists(*, user: User, tenant_id) -> bool:
    if user.is_superuser:
        return True
    return InstitutionMembership.objects.filter(user=user, institution_id=tenant_id, is_active=True).exists()


def _has_staff_authority(*, actor: User, tenant_id) -> bool:
    if actor.is_superuser:
        return True
    return InstitutionMembership.objects.filter(
        user=actor,
        institution_id=tenant_id,
        is_active=True,
        role__in=STAFF_ROLES,
    ).exists()


def _ensure_profile_access(*, actor: User, profile: LearnerLearningProfile, mutate: bool = False) -> None:
    if actor.id == profile.learner_id and _membership_exists(user=actor, tenant_id=profile.tenant_id):
        return
    if _has_staff_authority(actor=actor, tenant_id=profile.tenant_id):
        return
    raise PermissionDenied("LEARNING_IDENTITY_ACCESS_DENIED")


def _ensure_actor_can_manage(*, actor: User, tenant_id, learner_id) -> None:
    if actor.id == learner_id and _membership_exists(user=actor, tenant_id=tenant_id):
        return
    if _has_staff_authority(actor=actor, tenant_id=tenant_id):
        return
    raise PermissionDenied("LEARNING_IDENTITY_ACCESS_DENIED")


def _ensure_learner_in_tenant(*, learner: User, tenant_id) -> None:
    if not _membership_exists(user=learner, tenant_id=tenant_id):
        raise PermissionDenied("LEARNING_IDENTITY_TENANT_MISMATCH")


def _publish_after_commit(events: EventPublisher, event_name: str, payload: dict[str, Any]) -> None:
    transaction.on_commit(lambda: events.publish(BusinessEvent.create(event_name, payload=payload)))


def _event_payload(profile: LearnerLearningProfile, **extra) -> dict[str, Any]:
    payload = {
        "profile_id": str(profile.id),
        "tenant_id": str(profile.tenant_id),
        "learner_id": str(profile.learner_id),
        "profile_version": profile.version,
        "status": profile.status,
    }
    payload.update(extra)
    return payload


def _get_command(scope: str, key: str, fingerprint: str):
    if not key:
        return None
    record = LearningIdentityCommandRecord.objects.filter(scope=scope, idempotency_key=key).first()
    if not record:
        return None
    if record.payload_fingerprint != fingerprint:
        raise ValidationError("Idempotency key was reused with a different payload.", code="IDEMPOTENCY_CONFLICT")
    return record


def _record_command(scope: str, key: str, fingerprint: str, result) -> None:
    if not key:
        return
    LearningIdentityCommandRecord.objects.create(
        scope=scope,
        idempotency_key=key,
        payload_fingerprint=fingerprint,
        result_model=result._meta.label,
        result_id=result.id,
    )


class CreateLearningProfileService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, tenant, learner: User, actor: User, idempotency_key: str = ""):
        payload = {"tenant_id": str(tenant.id), "learner_id": str(learner.id), "actor_id": str(actor.id)}
        fp = _fingerprint(payload)
        if record := _get_command("learning_identity.profile.create", idempotency_key, fp):
            return LearnerLearningProfile.objects.get(id=record.result_id)

        _ensure_learner_in_tenant(learner=learner, tenant_id=tenant.id)
        _ensure_actor_can_manage(actor=actor, tenant_id=tenant.id, learner_id=learner.id)
        existing = LearnerLearningProfile.objects.filter(
            tenant=tenant,
            learner=learner,
        ).exclude(status=LearningProfileStatus.ARCHIVED).first()
        if existing:
            raise ValidationError("A non-archived learning profile already exists for this learner.", code="LEARNING_PROFILE_ALREADY_EXISTS")
        profile = LearnerLearningProfile.objects.create(tenant=tenant, learner=learner, status=LearningProfileStatus.DRAFT)
        _record_command("learning_identity.profile.create", idempotency_key, fp, profile)
        _publish_after_commit(self.events, "learning_identity.profile.created", _event_payload(profile))
        return profile


class CreateDraftProfileVersionService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, profile_id, actor: User, expected_version: int, idempotency_key: str = "", copy_current: bool = False):
        payload = {
            "profile_id": str(profile_id),
            "actor_id": str(actor.id),
            "expected_version": expected_version,
            "copy_current": copy_current,
        }
        fp = _fingerprint(payload)
        if record := _get_command("learning_identity.profile_version.create_draft", idempotency_key, fp):
            return LearningProfileVersion.objects.get(id=record.result_id)

        profile = LearnerLearningProfile.objects.select_for_update().get(id=profile_id)
        _ensure_profile_access(actor=actor, profile=profile, mutate=True)
        if profile.version != expected_version:
            raise ValidationError("Learning profile version conflict.", code="LEARNING_PROFILE_VERSION_CONFLICT")
        profile.ensure_can_receive_draft()
        if LearningProfileVersion.objects.filter(profile=profile, status=ProfileVersionStatus.DRAFT).exists():
            raise ValidationError("A draft profile version already exists.", code="LEARNING_PROFILE_DRAFT_EXISTS")
        next_number = (LearningProfileVersion.objects.filter(profile=profile).order_by("-version_number").values_list("version_number", flat=True).first() or 0) + 1
        draft = LearningProfileVersion.objects.create(profile=profile, version_number=next_number, created_by=actor)
        if copy_current and profile.current_version_id:
            for attribute in profile.current_version.attributes.order_by("attribute_type", "created_at"):
                LearningIdentityAttribute.objects.create(
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
        profile.version += 1
        profile.save(update_fields=["version", "updated_at"])
        _record_command("learning_identity.profile_version.create_draft", idempotency_key, fp, draft)
        _publish_after_commit(
            self.events,
            "learning_identity.profile_version.created",
            _event_payload(profile, profile_version_id=str(draft.id), version_number=draft.version_number),
        )
        return draft


class AddDeclaredIdentityAttributeService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(
        self,
        *,
        profile_version_id,
        actor: User,
        attribute_type: str,
        value,
        source_type: str = AttributeSourceType.LEARNER,
        source_reference: dict | None = None,
        valid_from=None,
        valid_until=None,
        visibility: str = AttributeVisibility.LEARNER_VISIBLE,
        review_required: bool = False,
        restricted: bool = False,
        idempotency_key: str = "",
    ):
        payload = {
            "profile_version_id": str(profile_version_id),
            "actor_id": str(actor.id),
            "attribute_type": attribute_type,
            "value": value,
            "source_type": source_type,
            "source_reference": source_reference or {},
            "valid_from": valid_from,
            "valid_until": valid_until,
            "visibility": visibility,
            "review_required": review_required,
            "restricted": restricted,
        }
        fp = _fingerprint(payload)
        if record := _get_command("learning_identity.attribute.declare", idempotency_key, fp):
            return LearningIdentityAttribute.objects.get(id=record.result_id)

        draft = LearningProfileVersion.objects.select_for_update().select_related("profile").get(id=profile_version_id)
        draft.ensure_draft()
        _ensure_profile_access(actor=actor, profile=draft.profile, mutate=True)
        if draft.profile.is_archived:
            raise ValidationError("Archived profiles cannot receive attributes.", code="PROFILE_ARCHIVED")
        normalized_value = validate_attribute_value(attribute_type, value)
        attribute = LearningIdentityAttribute(
            profile_version=draft,
            attribute_type=attribute_type,
            classification=AttributeClassification.DECLARED,
            value=normalized_value,
            value_schema_version=1,
            confidence=None,
            source_type=source_type,
            source_reference=source_reference or {},
            declared_at=timezone.now(),
            valid_from=valid_from,
            valid_until=valid_until,
            visibility=visibility,
            review_required=review_required,
            restricted=restricted,
            created_by=actor,
        )
        attribute.full_clean()
        attribute.save()
        _record_command("learning_identity.attribute.declare", idempotency_key, fp, attribute)
        _publish_after_commit(
            self.events,
            "learning_identity.attribute.declared",
            _event_payload(
                draft.profile,
                profile_version_id=str(draft.id),
                attribute_id=str(attribute.id),
                attribute_type=attribute.attribute_type,
                classification=attribute.classification,
                visibility=attribute.visibility,
                restricted=attribute.restricted,
            ),
        )
        return attribute


class PublishLearningProfileVersionService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, profile_version_id, actor: User, expected_version: int, idempotency_key: str = ""):
        payload = {
            "profile_version_id": str(profile_version_id),
            "actor_id": str(actor.id),
            "expected_version": expected_version,
        }
        fp = _fingerprint(payload)
        if record := _get_command("learning_identity.profile_version.publish", idempotency_key, fp):
            return LearningProfileVersion.objects.get(id=record.result_id)

        draft = LearningProfileVersion.objects.select_for_update().select_related("profile").get(id=profile_version_id)
        profile = LearnerLearningProfile.objects.select_for_update().get(id=draft.profile_id)
        _ensure_profile_access(actor=actor, profile=profile, mutate=True)
        if profile.version != expected_version:
            raise ValidationError("Learning profile version conflict.", code="LEARNING_PROFILE_VERSION_CONFLICT")
        if not draft.attributes.exists():
            raise ValidationError("A profile version requires at least one governed attribute before publication.", code="PROFILE_VERSION_ATTRIBUTES_REQUIRED")
        provenance = evaluate_profile_version_provenance(draft)
        if provenance.status == ProvenanceReadinessStatus.BLOCKED:
            raise ValidationError(provenance.blocking_codes, code="PROFILE_VERSION_PROVENANCE_BLOCKED")
        previous = profile.current_version
        draft.publish(actor=actor, supersedes=previous)
        draft.full_clean()
        draft.save(update_fields=["status", "published_by", "published_at", "supersedes_version"])
        if previous:
            previous.mark_superseded()
            previous.save(update_fields=["status", "superseded_at"])
        profile.current_version = draft
        if profile.status != LearningProfileStatus.RESTRICTED:
            profile.status = LearningProfileStatus.ACTIVE
        profile.version += 1
        profile.save(update_fields=["current_version", "status", "version", "updated_at"])
        _record_command("learning_identity.profile_version.publish", idempotency_key, fp, draft)
        if previous:
            _publish_after_commit(
                self.events,
                "learning_identity.profile_version.superseded",
                _event_payload(profile, profile_version_id=str(previous.id), superseded_by_version_id=str(draft.id)),
            )
        _publish_after_commit(
            self.events,
            "learning_identity.profile_version.published",
            _event_payload(profile, profile_version_id=str(draft.id), version_number=draft.version_number),
        )
        return draft


class RestrictLearningProfileService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, profile_id, actor: User, expected_version: int, reason: str = ""):
        profile = LearnerLearningProfile.objects.select_for_update().get(id=profile_id)
        if not _has_staff_authority(actor=actor, tenant_id=profile.tenant_id):
            raise PermissionDenied("LEARNING_IDENTITY_RESTRICT_DENIED")
        if profile.version != expected_version:
            raise ValidationError("Learning profile version conflict.", code="LEARNING_PROFILE_VERSION_CONFLICT")
        profile.restrict(reason=reason)
        profile.full_clean()
        profile.save(update_fields=["status", "restricted_at", "restriction_reason", "version", "updated_at"])
        _publish_after_commit(self.events, "learning_identity.profile.restricted", _event_payload(profile))
        return profile


class ArchiveLearningProfileService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, profile_id, actor: User, expected_version: int):
        profile = LearnerLearningProfile.objects.select_for_update().get(id=profile_id)
        _ensure_profile_access(actor=actor, profile=profile, mutate=True)
        if profile.version != expected_version:
            raise ValidationError("Learning profile version conflict.", code="LEARNING_PROFILE_VERSION_CONFLICT")
        profile.archive()
        profile.full_clean()
        profile.save(update_fields=["status", "archived_at", "version", "updated_at"])
        _publish_after_commit(self.events, "learning_identity.profile.archived", _event_payload(profile))
        return profile
