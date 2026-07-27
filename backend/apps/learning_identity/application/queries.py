from __future__ import annotations

from django.core.exceptions import PermissionDenied

from apps.users.domain.models import InstitutionMembership, InstitutionRole, User

from ..domain.enums import AttributeVisibility
from ..domain.models import LearnerLearningProfile
from .dto import LearnerSafeAttributeSummary, LearnerSafeProfileSummary


LEARNER_LABELS = {
    "PREFERRED_LEARNING_LANGUAGE": "Preferred learning language",
    "TARGET_QUALIFICATION": "Target qualification",
    "TARGET_EXAM_DATE": "Target exam date",
    "WEEKLY_STUDY_CAPACITY": "Weekly study capacity",
    "PRIOR_STUDY_EXPERIENCE": "Prior study experience",
    "ACCESSIBILITY_PREFERENCE": "Accessibility preference",
    "STUDY_GOAL": "Study goal",
    "PREFERRED_EXPLANATION_FORMAT": "Preferred explanation format",
    "PACING_SUPPORT_PREFERENCE": "Pacing support preference",
}

SOURCE_LABELS = {
    "LEARNER": "Declared by the learner",
    "AUTHORIZED_ACTOR": "Declared by an authorized actor",
    "ONBOARDING": "Declared during onboarding",
    "INSTITUTION": "Verified by an institution",
    "DIAGNOSTIC": "Derived from diagnostic authority",
    "ASSESSMENT": "Derived from assessment authority",
    "LEARNING_SESSION": "Derived from learning-session evidence",
    "SYSTEM_DERIVATION": "Calculated by platform policy",
}


def _has_access(actor: User, profile: LearnerLearningProfile) -> bool:
    if actor.id == profile.learner_id:
        return True
    if actor.is_superuser:
        return True
    return InstitutionMembership.objects.filter(
        user=actor,
        institution_id=profile.tenant_id,
        is_active=True,
        role__in=[
            InstitutionRole.ADMINISTRATOR,
            InstitutionRole.INSTITUTION_OWNER,
            InstitutionRole.SYSTEM_ADMINISTRATOR,
            InstitutionRole.TEACHER,
            InstitutionRole.REVIEWER,
        ],
    ).exists()


def _safe_value(attribute) -> str:
    if attribute.attribute_type == "WEEKLY_STUDY_CAPACITY":
        return f"{attribute.value} minutes per week"
    return str(attribute.value)


def _validity(attribute) -> str:
    if attribute.valid_from and attribute.valid_until:
        return f"Valid from {attribute.valid_from.isoformat()} until {attribute.valid_until.isoformat()}"
    if attribute.valid_from:
        return f"Valid from {attribute.valid_from.isoformat()}"
    if attribute.valid_until:
        return f"Valid until {attribute.valid_until.isoformat()}"
    return "Current declaration"


class GetLearnerSafeProfileSummary:
    def execute(self, *, profile_id, actor: User) -> LearnerSafeProfileSummary:
        profile = (
            LearnerLearningProfile.objects.select_related("current_version", "learner", "tenant")
            .prefetch_related("current_version__attributes")
            .get(id=profile_id)
        )
        if not _has_access(actor, profile):
            raise PermissionDenied("LEARNING_IDENTITY_ACCESS_DENIED")
        current = profile.current_version
        attributes: list[LearnerSafeAttributeSummary] = []
        if current:
            for attribute in current.attributes.order_by("attribute_type", "created_at"):
                if attribute.restricted or attribute.visibility != AttributeVisibility.LEARNER_VISIBLE:
                    continue
                attributes.append(
                    LearnerSafeAttributeSummary(
                        attribute_type=attribute.attribute_type,
                        learner_label=LEARNER_LABELS.get(attribute.attribute_type, "Learning identity attribute"),
                        learner_safe_value=_safe_value(attribute),
                        classification=attribute.classification,
                        source_summary=SOURCE_LABELS.get(attribute.source_type, "Governed learning identity source"),
                        validity_summary=_validity(attribute),
                        review_required=attribute.review_required,
                    )
                )
        return LearnerSafeProfileSummary(
            profile_id=str(profile.id),
            status=profile.status,
            current_version_number=current.version_number if current else None,
            last_updated_at=profile.updated_at.isoformat(),
            attributes=attributes,
        )
