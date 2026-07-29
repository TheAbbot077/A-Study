from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError

from apps.users.domain.models import InstitutionMembership, InstitutionRole, User

from ..domain.enums import JourneyAuthorityProviderType, LearningJourneySourceType, LearningJourneyType
from ..domain.models import InstitutionalLearningAssignment, LearningJourney


INSTITUTION_STAFF_ROLES = {
    InstitutionRole.ADMINISTRATOR,
    InstitutionRole.INSTITUTION_OWNER,
    InstitutionRole.SYSTEM_ADMINISTRATOR,
    InstitutionRole.TEACHER,
}


@dataclass(frozen=True)
class JourneyAuthority:
    provider: str
    institution_id: str
    learner_id: str
    subject_id: str = ""
    curriculum_reference_id: str = ""
    programme_label: str = ""
    course_label: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.provider,
            "institution_id": self.institution_id,
            "learner_id": self.learner_id,
            "subject_id": self.subject_id,
            "curriculum_reference_id": self.curriculum_reference_id,
            "programme": self.programme_label,
            "course": self.course_label,
        }


class JourneyAuthorityProvider:
    provider_type: str

    def authority_for(self, *, journey: LearningJourney) -> JourneyAuthority:
        raise NotImplementedError

    def can_read(self, *, actor: User, journey: LearningJourney) -> bool:
        raise NotImplementedError

    def can_progress(self, *, actor: User, journey: LearningJourney) -> bool:
        return self.can_read(actor=actor, journey=journey)

    def can_complete(self, *, actor: User, journey: LearningJourney) -> bool:
        return self.can_read(actor=actor, journey=journey)


class SelfStudyAuthorityProvider(JourneyAuthorityProvider):
    provider_type = JourneyAuthorityProviderType.SELF_STUDY

    def authority_for(self, *, journey: LearningJourney) -> JourneyAuthority:
        return JourneyAuthority(
            provider=self.provider_type,
            institution_id=str(journey.institution_id or ""),
            learner_id=str(journey.learner_id),
        )

    def can_read(self, *, actor: User, journey: LearningJourney) -> bool:
        return actor.is_superuser or actor.id == journey.learner_id


class InstitutionAuthorityProvider(JourneyAuthorityProvider):
    provider_type = JourneyAuthorityProviderType.INSTITUTION

    def authority_for(self, *, journey: LearningJourney) -> JourneyAuthority:
        assignment = InstitutionalLearningAssignment.objects.select_related("subject", "curriculum_reference").get(journey=journey)
        return JourneyAuthority(
            provider=self.provider_type,
            institution_id=str(assignment.institution_id),
            learner_id=str(assignment.learner_id),
            subject_id=str(assignment.subject_id or ""),
            curriculum_reference_id=str(assignment.curriculum_reference_id or ""),
            programme_label=assignment.programme_label,
            course_label=assignment.course_label,
        )

    def can_read(self, *, actor: User, journey: LearningJourney) -> bool:
        if actor.is_superuser or actor.id == journey.learner_id:
            return True
        return InstitutionMembership.objects.filter(
            user=actor,
            institution_id=journey.institution_id,
            is_active=True,
            role__in=INSTITUTION_STAFF_ROLES,
        ).exists()

    def can_progress(self, *, actor: User, journey: LearningJourney) -> bool:
        return self.can_read(actor=actor, journey=journey)

    def can_complete(self, *, actor: User, journey: LearningJourney) -> bool:
        if actor.is_superuser:
            return True
        return InstitutionMembership.objects.filter(
            user=actor,
            institution_id=journey.institution_id,
            is_active=True,
            role__in={InstitutionRole.ADMINISTRATOR, InstitutionRole.INSTITUTION_OWNER, InstitutionRole.SYSTEM_ADMINISTRATOR},
        ).exists()


class JourneyAuthorityResolver:
    def provider_for(self, *, journey: LearningJourney) -> JourneyAuthorityProvider:
        binding = journey.source_bindings.first()
        if journey.journey_type == LearningJourneyType.INSTITUTIONAL:
            return InstitutionAuthorityProvider()
        if binding and binding.source_type == LearningJourneySourceType.SELF_STUDY_WORKSPACE:
            return SelfStudyAuthorityProvider()
        if journey.journey_type == LearningJourneyType.SELF_STUDY:
            return SelfStudyAuthorityProvider()
        raise ValidationError("Journey authority provider is unavailable.", code="JOURNEY_AUTHORITY_PROVIDER_UNAVAILABLE")

    def require_can_read(self, *, actor: User, journey: LearningJourney) -> JourneyAuthorityProvider:
        provider = self.provider_for(journey=journey)
        if not provider.can_read(actor=actor, journey=journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        return provider
