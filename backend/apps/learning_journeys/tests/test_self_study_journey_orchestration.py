from django.core.exceptions import PermissionDenied
from django.test import TestCase
from rest_framework.test import APIClient

from apps.learning_journeys.application.action_policy import SelfStudyJourneyActionPolicy
from apps.learning_journeys.application.commands import ExecuteLearningJourneyActionCommand
from apps.learning_journeys.application.orchestration import SelfStudyJourneyOrchestrator
from apps.learning_journeys.application.queries import GetLearningJourneyService
from apps.learning_journeys.application.services import CreateLearningJourneyService
from apps.learning_journeys.domain.enums import LearningJourneyActionCode, LearningJourneyActionReceiptStatus, LearningJourneyStatus
from apps.learning_journeys.domain.models import LearningJourneyActionReceipt
from apps.self_study.onboarding_models import SelfStudyOnboarding
from apps.self_study.workspace_models import SelfStudyWorkspace
from apps.users.models import Institution, InstitutionMembership, InstitutionRole, User


class SelfStudyJourneyActionPolicyTests(TestCase):
    def setUp(self):
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.institution = Institution.objects.create(name="Learner Space", slug="learner-space", institution_type="individual")
        InstitutionMembership.objects.create(user=self.learner, institution=self.institution, role=InstitutionRole.STUDENT)
        self.workspace = SelfStudyWorkspace.objects.create(learner=self.learner, tenant=self.institution, display_name="Biology")
        self.journey = CreateLearningJourneyService().for_self_study_workspace(workspace_id=self.workspace.id, actor=self.learner)

    def test_policy_allows_begin_goal_discovery_and_rejects_unregistered_action(self):
        policy = SelfStudyJourneyActionPolicy()

        available, reason = policy.availability(journey=self.journey, action_code=LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY)
        self.assertTrue(available)
        self.assertEqual(reason, "")

        available, reason = policy.availability(journey=self.journey, action_code="DELETE_EVERYTHING")
        self.assertFalse(available)
        self.assertEqual(reason, "Journey action is not registered.")

    def test_policy_marks_unimplemented_downstream_action_unavailable(self):
        type(self.journey).objects.filter(id=self.journey.id).update(status=LearningJourneyStatus.PLAN_READY)
        self.journey.refresh_from_db()

        available, reason = SelfStudyJourneyActionPolicy().availability(
            journey=self.journey,
            action_code=LearningJourneyActionCode.ACTIVATE_LEARNING_PLAN,
        )

        self.assertFalse(available)
        self.assertIn("authoritative", reason)


class SelfStudyJourneyOrchestratorTests(TestCase):
    def setUp(self):
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.other = User.objects.create_user(email="other@example.com", password="test")
        self.institution = Institution.objects.create(name="Learner Space", slug="learner-space", institution_type="individual")
        InstitutionMembership.objects.create(user=self.learner, institution=self.institution, role=InstitutionRole.STUDENT)
        self.workspace = SelfStudyWorkspace.objects.create(learner=self.learner, tenant=self.institution, display_name="Biology")
        self.journey = CreateLearningJourneyService().for_self_study_workspace(workspace_id=self.workspace.id, actor=self.learner)

    def command(self, action_code, *, key="key-1", payload=None, actor=None):
        actor = actor or self.learner
        return ExecuteLearningJourneyActionCommand(
            journey_id=str(self.journey.id),
            action_code=action_code,
            actor_id=str(actor.id),
            idempotency_key=key,
            payload=payload or {},
        )

    def test_begin_goal_discovery_delegates_to_onboarding_and_records_receipt(self):
        result = SelfStudyJourneyOrchestrator().execute(
            command=self.command(LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY),
            actor=self.learner,
        )

        self.assertEqual(result["receipt"]["status"], LearningJourneyActionReceiptStatus.SUCCEEDED)
        self.assertEqual(result["journey"]["state"], LearningJourneyStatus.DISCOVERING_GOAL)
        self.assertEqual(SelfStudyOnboarding.objects.filter(workspace=self.workspace).count(), 1)
        receipt = LearningJourneyActionReceipt.objects.get(journey=self.journey)
        self.assertEqual(receipt.action_code, LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY)
        self.assertEqual(receipt.source_capability, "self_study.onboarding")

    def test_duplicate_idempotency_key_replays_existing_receipt(self):
        orchestrator = SelfStudyJourneyOrchestrator()
        first = orchestrator.execute(command=self.command(LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY), actor=self.learner)
        second = orchestrator.execute(command=self.command(LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY), actor=self.learner)

        self.assertEqual(first["receipt"]["id"], second["receipt"]["id"])
        self.assertTrue(second["receipt"]["replayed"])
        self.assertEqual(LearningJourneyActionReceipt.objects.count(), 1)

    def test_unavailable_action_is_rejected_and_does_not_mutate_journey(self):
        result = SelfStudyJourneyOrchestrator().execute(
            command=self.command(LearningJourneyActionCode.SELECT_CURRICULUM, key="select-too-early", payload={"candidate_id": "11111111-1111-4111-8111-111111111111"}),
            actor=self.learner,
        )

        self.assertEqual(result["receipt"]["status"], LearningJourneyActionReceiptStatus.REJECTED)
        self.assertEqual(result["receipt"]["failure_code"], "LEARNING_JOURNEY_ACTION_NOT_AVAILABLE")
        self.journey.refresh_from_db()
        self.assertEqual(self.journey.status, LearningJourneyStatus.DISCOVERING_GOAL)

    def test_actor_mismatch_is_denied_before_action_receipt(self):
        with self.assertRaises(PermissionDenied):
            SelfStudyJourneyOrchestrator().execute(
                command=self.command(LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY, actor=self.other),
                actor=self.learner,
            )

        self.assertEqual(LearningJourneyActionReceipt.objects.count(), 0)

    def test_read_contract_includes_progress_and_active_capabilities(self):
        SelfStudyJourneyOrchestrator().execute(command=self.command(LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY), actor=self.learner)

        payload = GetLearningJourneyService().execute(journey_id=self.journey.id, actor=self.learner)

        self.assertEqual(payload["progress"]["phase"], "GOAL_DISCOVERY")
        self.assertIn("active_capabilities", payload)
        self.assertIn("intent_id", payload["active_capabilities"])


class SelfStudyJourneyActionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.institution = Institution.objects.create(name="Learner Space", slug="learner-space", institution_type="individual")
        InstitutionMembership.objects.create(user=self.learner, institution=self.institution, role=InstitutionRole.STUDENT)
        self.workspace = SelfStudyWorkspace.objects.create(learner=self.learner, tenant=self.institution, display_name="Biology")
        self.journey = CreateLearningJourneyService().for_self_study_workspace(workspace_id=self.workspace.id, actor=self.learner)

    def test_action_endpoint_executes_registered_action_and_returns_receipt_and_journey(self):
        self.client.force_authenticate(self.learner)

        response = self.client.post(
            f"/api/learning-journeys/{self.journey.id}/actions/begin-goal-discovery/",
            {"idempotency_key": "api-begin", "payload": {}},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["receipt"]["status"], LearningJourneyActionReceiptStatus.SUCCEEDED)
        self.assertEqual(response.data["journey"]["state"], LearningJourneyStatus.DISCOVERING_GOAL)

    def test_action_endpoint_rejects_unavailable_action_safely(self):
        self.client.force_authenticate(self.learner)

        response = self.client.post(
            f"/api/learning-journeys/{self.journey.id}/actions/select-curriculum/",
            {"idempotency_key": "api-reject", "payload": {"candidate_id": "11111111-1111-4111-8111-111111111111"}},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["receipt"]["status"], LearningJourneyActionReceiptStatus.REJECTED)
        self.assertEqual(response.data["journey"]["state"], LearningJourneyStatus.DISCOVERING_GOAL)
