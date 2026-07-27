from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError

from apps.users.domain.models import InstitutionMembership, InstitutionRole, User

from ..domain.enums import (
    AttributeClassification,
    AttributeVisibility,
    LearnerPreferenceStatus,
    LearningIdentityTimelineEventType,
    LearningObservationStatus,
    MentorContextPurpose,
    ProfileVersionStatus,
)
from ..domain.models import (
    LearnerLearningProfile,
    LearnerPreferenceSelection,
    LearningIdentityAttribute,
    LearningIdentityCorrectionRequest,
    LearningIdentityObservation,
)
from ..domain.preferences import PREFERENCE_REGISTRY
from .queries import LEARNER_LABELS, SOURCE_LABELS


STAFF_ROLES = [
    InstitutionRole.ADMINISTRATOR,
    InstitutionRole.INSTITUTION_OWNER,
    InstitutionRole.SYSTEM_ADMINISTRATOR,
    InstitutionRole.TEACHER,
    InstitutionRole.REVIEWER,
]


@dataclass(frozen=True)
class LearnerMemoryItem:
    id: str
    kind: str
    label: str
    value: str
    classification: str
    source_summary: str
    last_updated_at: str
    status: str
    currently_used: bool
    allowed_actions: list[str]


@dataclass(frozen=True)
class LearnerTimelineEntry:
    timeline_id: str
    occurred_at: str
    recorded_at: str
    event_type: str
    title: str
    description: str
    classification: str
    disposition: str
    source_summary: str
    related_profile_version: int | None


@dataclass(frozen=True)
class MentorContextItem:
    key: str
    label: str
    value: Any
    source: str


def _can_access(actor: User, profile: LearnerLearningProfile) -> bool:
    if actor.id == profile.learner_id:
        return True
    if actor.is_superuser:
        return True
    return InstitutionMembership.objects.filter(user=actor, institution_id=profile.tenant_id, is_active=True, role__in=STAFF_ROLES).exists()


def _profile(profile_id, actor: User) -> LearnerLearningProfile:
    profile = LearnerLearningProfile.objects.select_related("current_version", "tenant", "learner").get(id=profile_id)
    if not _can_access(actor, profile):
        raise PermissionDenied("LEARNING_IDENTITY_ACCESS_DENIED")
    return profile


def _safe_attribute_value(attribute: LearningIdentityAttribute) -> str:
    if attribute.attribute_type == "WEEKLY_STUDY_CAPACITY":
        return f"{attribute.value} minutes per week"
    return str(attribute.value)


class GetLearnerMemorySummary:
    def execute(self, *, profile_id, actor: User) -> dict[str, Any]:
        profile = _profile(profile_id, actor)
        attributes: list[LearnerMemoryItem] = []
        if profile.current_version_id:
            for attribute in profile.current_version.attributes.order_by("attribute_type", "created_at"):
                if attribute.restricted or attribute.visibility != AttributeVisibility.LEARNER_VISIBLE:
                    continue
                actions = []
                if attribute.classification == AttributeClassification.DECLARED:
                    actions = ["replace", "withdraw"]
                elif attribute.classification == AttributeClassification.OBSERVED:
                    actions = ["contest"]
                attributes.append(
                    LearnerMemoryItem(
                        id=str(attribute.id),
                        kind="attribute",
                        label=LEARNER_LABELS.get(attribute.attribute_type, "Learning memory"),
                        value=_safe_attribute_value(attribute),
                        classification=attribute.classification,
                        source_summary=SOURCE_LABELS.get(attribute.source_type, "Governed learning identity source"),
                        last_updated_at=attribute.created_at.isoformat(),
                        status="current",
                        currently_used=not attribute.review_required,
                        allowed_actions=actions,
                    )
                )
        observations = [
            LearnerMemoryItem(
                id=str(observation.id),
                kind="observation",
                label=observation.safe_title,
                value=observation.safe_summary or observation.safe_title,
                classification="OBSERVED",
                source_summary=_observation_source(observation),
                last_updated_at=observation.updated_at.isoformat(),
                status=observation.status,
                currently_used=observation.status == LearningObservationStatus.ACTIVE and observation.mentor_context_eligible,
                allowed_actions=["contest"] if observation.status == LearningObservationStatus.ACTIVE else [],
            )
            for observation in LearningIdentityObservation.objects.filter(profile=profile, learner_visible=True).order_by("-occurred_at", "-created_at")[:10]
        ]
        preferences = [
            LearnerMemoryItem(
                id=str(preference.id),
                kind="preference",
                label=PREFERENCE_REGISTRY[preference.preference_key].label,
                value=_preference_value(preference.value),
                classification="PREFERENCE",
                source_summary="Chosen by you",
                last_updated_at=preference.created_at.isoformat(),
                status=preference.status,
                currently_used=preference.status == LearnerPreferenceStatus.ACTIVE,
                allowed_actions=["update", "withdraw"],
            )
            for preference in LearnerPreferenceSelection.objects.filter(profile=profile, status=LearnerPreferenceStatus.ACTIVE).order_by("preference_key")
            if preference.preference_key in PREFERENCE_REGISTRY
        ]
        return {
            "profile_id": str(profile.id),
            "tenant_id": str(profile.tenant_id),
            "learner_id": str(profile.learner_id),
            "status": profile.status,
            "profile_version": profile.version,
            "current_version_number": profile.current_version.version_number if profile.current_version else None,
            "what_abbot_remembers": [asdict(item) for item in attributes],
            "recent_learning_activity": [asdict(item) for item in observations],
            "study_preferences": [asdict(item) for item in preferences],
            "allowed_actions": ["update_declaration", "withdraw_declaration", "set_preference", "withdraw_preference", "contest_observation"],
        }


class ListLearningIdentityTimeline:
    def execute(self, *, profile_id, actor: User, limit: int = 50) -> dict[str, Any]:
        profile = _profile(profile_id, actor)
        entries: list[LearnerTimelineEntry] = []
        for version in profile.profile_versions.order_by("-created_at")[:limit]:
            if version.status == ProfileVersionStatus.PUBLISHED:
                entries.append(
                    LearnerTimelineEntry(
                        timeline_id=f"profile-version:{version.id}",
                        occurred_at=(version.published_at or version.created_at).isoformat(),
                        recorded_at=version.created_at.isoformat(),
                        event_type=LearningIdentityTimelineEventType.PROFILE_PUBLISHED,
                        title="Learning profile updated",
                        description="Abbot updated what it can safely remember.",
                        classification="PROFILE",
                        disposition=version.status,
                        source_summary="Learning identity governance",
                        related_profile_version=version.version_number,
                    )
                )
        for observation in LearningIdentityObservation.objects.filter(profile=profile, learner_visible=True).order_by("-occurred_at", "-created_at")[:limit]:
            entries.append(
                LearnerTimelineEntry(
                    timeline_id=f"observation:{observation.id}",
                    occurred_at=observation.occurred_at.isoformat(),
                    recorded_at=observation.created_at.isoformat(),
                    event_type=LearningIdentityTimelineEventType.OBSERVATION_RECORDED if observation.status != LearningObservationStatus.CONTESTED else LearningIdentityTimelineEventType.OBSERVATION_CONTESTED,
                    title=observation.safe_title,
                    description=observation.safe_summary or "Recorded from a governed learning activity.",
                    classification="OBSERVED",
                    disposition=observation.status,
                    source_summary=_observation_source(observation),
                    related_profile_version=profile.current_version.version_number if profile.current_version else None,
                )
            )
        for preference in LearnerPreferenceSelection.objects.filter(profile=profile).order_by("-created_at")[:limit]:
            event_type = LearningIdentityTimelineEventType.PREFERENCE_WITHDRAWN if preference.status == LearnerPreferenceStatus.WITHDRAWN else LearningIdentityTimelineEventType.PREFERENCE_SELECTED
            entries.append(
                LearnerTimelineEntry(
                    timeline_id=f"preference:{preference.id}",
                    occurred_at=preference.created_at.isoformat(),
                    recorded_at=preference.created_at.isoformat(),
                    event_type=event_type,
                    title=f"{PREFERENCE_REGISTRY.get(preference.preference_key).label if preference.preference_key in PREFERENCE_REGISTRY else 'Preference'} updated",
                    description="You changed a study preference.",
                    classification="PREFERENCE",
                    disposition=preference.status,
                    source_summary="Chosen by you",
                    related_profile_version=profile.current_version.version_number if profile.current_version else None,
                )
            )
        for correction in LearningIdentityCorrectionRequest.objects.filter(profile=profile).order_by("-requested_at")[:limit]:
            entries.append(
                LearnerTimelineEntry(
                    timeline_id=f"correction:{correction.id}",
                    occurred_at=correction.requested_at.isoformat(),
                    recorded_at=correction.requested_at.isoformat(),
                    event_type=LearningIdentityTimelineEventType.OBSERVATION_CONTESTED if correction.action == "CONTEST_OBSERVATION" else LearningIdentityTimelineEventType.DECLARATION_WITHDRAWN,
                    title="Memory review requested",
                    description="You asked Abbot to review or update a memory.",
                    classification="CORRECTION",
                    disposition=correction.status,
                    source_summary="Requested by you",
                    related_profile_version=profile.current_version.version_number if profile.current_version else None,
                )
            )
        entries = sorted(entries, key=lambda entry: (entry.occurred_at, entry.timeline_id), reverse=True)[:limit]
        return {"profile_id": str(profile.id), "entries": [asdict(entry) for entry in entries]}


class BuildLearnerMentorContext:
    def execute(self, *, profile_id, actor: User, purpose: str) -> dict[str, Any]:
        if purpose not in MentorContextPurpose.values:
            raise ValidationError("Unsupported mentor context purpose.", code="UNSUPPORTED_MENTOR_CONTEXT_PURPOSE")
        profile = _profile(profile_id, actor)
        items: list[MentorContextItem] = []
        if profile.current_version_id:
            for attribute in profile.current_version.attributes.filter(visibility=AttributeVisibility.LEARNER_VISIBLE, restricted=False, review_required=False).order_by("attribute_type"):
                if attribute.classification not in {AttributeClassification.DECLARED, AttributeClassification.VERIFIED}:
                    continue
                items.append(
                    MentorContextItem(
                        key=attribute.attribute_type.lower(),
                        label=LEARNER_LABELS.get(attribute.attribute_type, "Learning memory"),
                        value=attribute.value,
                        source=SOURCE_LABELS.get(attribute.source_type, "Governed learning identity source"),
                    )
                )
        preferences = LearnerPreferenceSelection.objects.filter(profile=profile, status=LearnerPreferenceStatus.ACTIVE).order_by("preference_key")
        for preference in preferences:
            definition = PREFERENCE_REGISTRY.get(preference.preference_key)
            if not definition:
                continue
            if purpose == MentorContextPurpose.TEACHING_PERSONALIZATION and not preference.teaching_context_eligible:
                continue
            if purpose in {MentorContextPurpose.SESSION_OPENING, MentorContextPurpose.STUDY_PLANNING} and not preference.mentor_context_eligible:
                continue
            items.append(MentorContextItem(key=preference.preference_key.lower(), label=definition.label, value=preference.value, source="Chosen by you"))
        recent = LearningIdentityObservation.objects.filter(
            profile=profile,
            status=LearningObservationStatus.ACTIVE,
            mentor_context_eligible=True,
        ).order_by("-occurred_at")[:3]
        for observation in recent:
            items.append(MentorContextItem(key=f"activity_{observation.id}", label=observation.safe_title, value=observation.safe_summary or observation.safe_title, source=_observation_source(observation)))
        return {
            "profile_id": str(profile.id),
            "purpose": purpose,
            "profile_version": profile.current_version.version_number if profile.current_version else None,
            "items": [asdict(item) for item in items],
        }


def _preference_value(value: Any) -> str:
    if isinstance(value, bool):
        return "On" if value else "Off"
    return str(value).replace("_", " ")


def _observation_source(observation: LearningIdentityObservation) -> str:
    if observation.source_type == "DIAGNOSTIC_ATTEMPT":
        return "Recorded after a completed diagnostic"
    if observation.source_type == "LEARNING_SESSION":
        return "Recorded from a governed learning session"
    return "Recorded from governed learning activity"
