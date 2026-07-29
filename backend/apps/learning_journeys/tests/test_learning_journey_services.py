from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from apps.learning_journeys.application.queries import GetLearningJourneyService
from apps.learning_journeys.application.services import CreateLearningJourneyService, LearningJourneyLifecycleService, SynchronizeLearningJourneyService
from apps.learning_journeys.domain.enums import LearningJourneyBlockerCode, LearningJourneyStatus, LearningJourneyType
from apps.learning_journeys.domain.models import LearningJourney, LearningJourneySourceBinding
from apps.self_study.workspace_models import SelfStudyWorkspace
from apps.users.models import Institution, InstitutionMembership, InstitutionRole, User


class LearningJourneyServiceTests(TestCase):
    def setUp(self):
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.other = User.objects.create_user(email="other@example.com", password="test")
        self.institution = Institution.objects.create(name="Learner Space", slug="learner-space", institution_type="individual")
        InstitutionMembership.objects.create(user=self.learner, institution=self.institution, role=InstitutionRole.STUDENT)
        self.workspace = SelfStudyWorkspace.objects.create(
            learner=self.learner,
            tenant=self.institution,
            display_name="Biology",
        )

    def test_create_self_study_journey_is_idempotent_for_workspace(self):
        service = CreateLearningJourneyService()

        first = service.for_self_study_workspace(workspace_id=self.workspace.id, actor=self.learner)
        second = service.for_self_study_workspace(workspace_id=self.workspace.id, actor=self.learner)

        self.assertEqual(first.id, second.id)
        self.assertEqual(LearningJourney.objects.count(), 1)
        self.assertEqual(LearningJourneySourceBinding.objects.count(), 1)
        self.assertEqual(first.status, LearningJourneyStatus.DISCOVERING_GOAL)

    def test_other_learner_cannot_create_journey_for_workspace(self):
        with self.assertRaises(PermissionDenied):
            CreateLearningJourneyService().for_self_study_workspace(workspace_id=self.workspace.id, actor=self.other)

    def test_read_projection_exposes_current_step_actions_and_blockers(self):
        journey = CreateLearningJourneyService().for_self_study_workspace(workspace_id=self.workspace.id, actor=self.learner)

        payload = GetLearningJourneyService().execute(journey_id=journey.id, actor=self.learner)

        self.assertEqual(payload["journey_type"], LearningJourneyType.SELF_STUDY)
        self.assertEqual(payload["state"], LearningJourneyStatus.DISCOVERING_GOAL)
        self.assertEqual(payload["current_step"]["code"], "DISCOVER_GOAL")
        self.assertIn("available_actions", payload)
        self.assertEqual(payload["blockers"][0]["code"], LearningJourneyBlockerCode.NO_CONFIRMED_INTENT)
        self.assertNotIn("_state", payload)

    def test_other_learner_cannot_read_private_self_study_journey(self):
        journey = CreateLearningJourneyService().for_self_study_workspace(workspace_id=self.workspace.id, actor=self.learner)

        with self.assertRaises(PermissionDenied):
            GetLearningJourneyService().execute(journey_id=journey.id, actor=self.other)

    def test_synchronization_is_idempotent_without_state_change(self):
        journey = CreateLearningJourneyService().for_self_study_workspace(workspace_id=self.workspace.id, actor=self.learner)
        version = journey.version

        synchronized = SynchronizeLearningJourneyService().execute(journey_id=journey.id, actor=self.learner)

        self.assertEqual(synchronized.status, LearningJourneyStatus.DISCOVERING_GOAL)
        self.assertEqual(synchronized.version, version)

    def test_pause_and_resume_use_services(self):
        journey = CreateLearningJourneyService().for_self_study_workspace(workspace_id=self.workspace.id, actor=self.learner)
        lifecycle = LearningJourneyLifecycleService()

        paused = lifecycle.pause(journey_id=journey.id, actor=self.learner, expected_version=journey.version)
        self.assertEqual(paused.status, LearningJourneyStatus.PAUSED)
        paused_payload = GetLearningJourneyService().execute(journey_id=journey.id, actor=self.learner)
        self.assertEqual(paused_payload["state"], LearningJourneyStatus.PAUSED)
        self.assertEqual(paused_payload["available_actions"][0]["code"], "RESUME_JOURNEY")

        resumed = lifecycle.resume(journey_id=journey.id, actor=self.learner, expected_version=paused.version)
        self.assertEqual(resumed.status, LearningJourneyStatus.DISCOVERING_GOAL)

    def test_stale_expected_version_is_rejected(self):
        journey = CreateLearningJourneyService().for_self_study_workspace(workspace_id=self.workspace.id, actor=self.learner)

        with self.assertRaises(ValidationError):
            LearningJourneyLifecycleService().pause(journey_id=journey.id, actor=self.learner, expected_version=journey.version + 10)


class InstitutionalLearningJourneyServiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@example.com", password="test")
        self.learner = User.objects.create_user(email="student@example.com", password="test")
        self.institution = Institution.objects.create(name="Demo School", slug="demo-school", institution_type="school")
        InstitutionMembership.objects.create(user=self.admin, institution=self.institution, role=InstitutionRole.ADMINISTRATOR)

    def test_institutional_journey_requires_active_learner_membership(self):
        with self.assertRaises(ValidationError):
            CreateLearningJourneyService().for_institutional_membership(
                learner_id=self.learner.id,
                institution_id=self.institution.id,
                actor=self.admin,
            )

    def test_institutional_projection_is_structural_and_does_not_fabricate_course(self):
        InstitutionMembership.objects.create(user=self.learner, institution=self.institution, role=InstitutionRole.STUDENT)

        journey = CreateLearningJourneyService().for_institutional_membership(
            learner_id=self.learner.id,
            institution_id=self.institution.id,
            actor=self.admin,
        )
        payload = GetLearningJourneyService().execute(journey_id=journey.id, actor=self.admin)

        self.assertEqual(payload["journey_type"], LearningJourneyType.INSTITUTIONAL)
        self.assertEqual(payload["state"], LearningJourneyStatus.SUBJECT_BINDING_REQUIRED)
        self.assertEqual(payload["blockers"][0]["code"], LearningJourneyBlockerCode.INSTITUTIONAL_ASSIGNMENT_REQUIRED)
        self.assertEqual(payload["authority"]["type"], "INSTITUTION")
