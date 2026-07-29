from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.academic.models import Subject
from apps.learning_journeys.domain.enums import (
    LearningJourneySourceType,
    LearningJourneyStatus,
    LearningJourneyStatusReasonCode,
    LearningJourneySubjectBindingSource,
    LearningJourneySubjectBindingStatus,
    LearningJourneyType,
)
from apps.learning_journeys.domain.models import LearningJourney, LearningJourneySourceBinding, LearningJourneySubjectBinding
from apps.users.models import Institution, User


class LearningJourneyDomainTests(TestCase):
    def setUp(self):
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.institution = Institution.objects.create(name="Learner Space", slug="learner-space", institution_type="individual")

    def test_self_study_journey_can_start_discovering_goal(self):
        journey = LearningJourney.objects.create(
            learner=self.learner,
            institution=self.institution,
            journey_type=LearningJourneyType.SELF_STUDY,
        )

        changed = journey.transition_to(
            LearningJourneyStatus.DISCOVERING_GOAL,
            reason_code=LearningJourneyStatusReasonCode.INTENT_NOT_CONFIRMED,
            current_step_code="DISCOVER_GOAL",
        )

        self.assertTrue(changed)
        self.assertEqual(journey.status, LearningJourneyStatus.DISCOVERING_GOAL)
        self.assertEqual(journey.version, 2)

    def test_institutional_journey_requires_institution(self):
        journey = LearningJourney(learner=self.learner, journey_type=LearningJourneyType.INSTITUTIONAL)

        with self.assertRaises(ValidationError):
            journey.full_clean()

    def test_journey_type_and_learner_are_immutable(self):
        other = User.objects.create_user(email="other@example.com", password="test")
        journey = LearningJourney.objects.create(
            learner=self.learner,
            institution=self.institution,
            journey_type=LearningJourneyType.SELF_STUDY,
        )

        journey.journey_type = LearningJourneyType.INSTITUTIONAL
        with self.assertRaises(ValidationError):
            journey.save()

        journey.refresh_from_db()
        journey.learner = other
        with self.assertRaises(ValidationError):
            journey.save()

    def test_invalid_lifecycle_transition_is_rejected(self):
        journey = LearningJourney.objects.create(
            learner=self.learner,
            institution=self.institution,
            journey_type=LearningJourneyType.SELF_STUDY,
        )

        with self.assertRaises(ValidationError):
            journey.transition_to(
                LearningJourneyStatus.LEARNING_ACTIVE,
                reason_code=LearningJourneyStatusReasonCode.LEARNING_PLAN_REQUIRED,
                current_step_code="BEGIN_LEARNING",
            )

    def test_terminal_journey_cannot_return_to_active(self):
        journey = LearningJourney.objects.create(
            learner=self.learner,
            institution=self.institution,
            journey_type=LearningJourneyType.SELF_STUDY,
        )
        journey.transition_to(
            LearningJourneyStatus.DISCOVERING_GOAL,
            reason_code=LearningJourneyStatusReasonCode.INTENT_NOT_CONFIRMED,
            current_step_code="DISCOVER_GOAL",
        )
        journey.transition_to(
            LearningJourneyStatus.WITHDRAWN,
            reason_code=LearningJourneyStatusReasonCode.WITHDRAWN_BY_LEARNER,
            current_step_code="DISCOVER_GOAL",
        )

        with self.assertRaises(ValidationError):
            journey.transition_to(
                LearningJourneyStatus.DISCOVERING_GOAL,
                reason_code=LearningJourneyStatusReasonCode.INTENT_NOT_CONFIRMED,
                current_step_code="DISCOVER_GOAL",
            )

    def test_subject_binding_has_one_active_binding_and_supersedes_durably(self):
        journey = LearningJourney.objects.create(
            learner=self.learner,
            institution=self.institution,
            journey_type=LearningJourneyType.SELF_STUDY,
        )
        subject = Subject.objects.create(institution=self.institution, code="BIO", name="Biology")
        binding = LearningJourneySubjectBinding.objects.create(
            journey=journey,
            subject=subject,
            binding_source=LearningJourneySubjectBindingSource.SELF_STUDY_CURRICULUM_RESOLUTION,
        )

        self.assertEqual(binding.status, LearningJourneySubjectBindingStatus.ACTIVE)
        self.assertTrue(binding.supersede())
        binding.save()

        self.assertEqual(binding.status, LearningJourneySubjectBindingStatus.SUPERSEDED)
        self.assertIsNotNone(binding.superseded_at)

    def test_source_binding_is_unique_for_source(self):
        journey = LearningJourney.objects.create(
            learner=self.learner,
            institution=self.institution,
            journey_type=LearningJourneyType.SELF_STUDY,
        )
        source_id = "11111111-1111-4111-8111-111111111111"
        LearningJourneySourceBinding.objects.create(
            journey=journey,
            source_type=LearningJourneySourceType.SELF_STUDY_WORKSPACE,
            source_id=source_id,
        )

        with self.assertRaises(Exception):
            LearningJourneySourceBinding.objects.create(
                journey=journey,
                source_type=LearningJourneySourceType.SELF_STUDY_WORKSPACE,
                source_id=source_id,
            )
