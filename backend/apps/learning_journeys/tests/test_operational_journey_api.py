from django.test import TestCase
from rest_framework.test import APIClient

from apps.learning_journeys.application.operational import LearningJourneyIntegrityService
from apps.learning_journeys.domain.enums import (
    LearningJourneyActionCode,
    LearningJourneyActionReceiptStatus,
    LearningJourneyIntegrityFindingCode,
    LearningJourneyIntegrityFindingStatus,
    LearningJourneyStatus,
)
from apps.learning_journeys.domain.models import LearningJourney, LearningJourneyActionReceipt, LearningJourneyIntegrityFinding, LearningJourneyOperation
from apps.self_study.workspace_models import SelfStudyWorkspace
from apps.users.models import Institution, InstitutionMembership, InstitutionRole, User


class OperationalJourneyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.other = User.objects.create_user(email="other@example.com", password="test")
        self.institution = Institution.objects.create(name="Learner Space", slug="learner-space", institution_type="individual")
        InstitutionMembership.objects.create(user=self.learner, institution=self.institution, role=InstitutionRole.STUDENT)
        self.workspace = SelfStudyWorkspace.objects.create(
            learner=self.learner,
            tenant=self.institution,
            display_name="Biology",
        )

    def _journey(self):
        self.client.force_authenticate(self.learner)
        created = self.client.post("/api/learning-journeys/self-study/", {"workspace_id": str(self.workspace.id)}, format="json")
        self.assertEqual(created.status_code, 201)
        return created.data

    def test_canonical_view_contains_operational_sections(self):
        journey = self._journey()

        response = self.client.get(f"/api/learning-journeys/{journey['journey_id']}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], response.data["state"])
        self.assertIn("authority", response.data)
        self.assertIn("current_step", response.data)
        self.assertIn("active_context", response.data)
        self.assertIn("available_actions", response.data)
        self.assertIn("recent_activity", response.data)
        self.assertIn("operational_metadata", response.data)
        self.assertEqual(response.data["authority"]["type"], "SELF_STUDY")

    def test_active_endpoint_is_deterministic(self):
        self._journey()

        response = self.client.get("/api/learning-journeys/active/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.data["result"], {"ONE", "MULTIPLE"})

    def test_action_endpoint_returns_version_conflict_receipt(self):
        journey = self._journey()

        response = self.client.post(
            f"/api/learning-journeys/{journey['journey_id']}/actions/{LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY}/",
            {
                "idempotency_key": "begin-1",
                "expected_journey_version": journey["version"] - 1,
                "payload": {},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["receipt"]["status"], LearningJourneyActionReceiptStatus.CONFLICT)
        self.assertEqual(response.data["receipt"]["failure_code"], "JOURNEY_VERSION_CONFLICT")
        self.assertEqual(LearningJourneyOperation.objects.filter(journey_id=journey["journey_id"]).count(), 1)

    def test_idempotency_payload_mismatch_is_conflict(self):
        journey = self._journey()
        url = f"/api/learning-journeys/{journey['journey_id']}/actions/{LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY}/"
        first = self.client.post(url, {"idempotency_key": "same-key", "payload": {}}, format="json")

        second = self.client.post(url, {"idempotency_key": "same-key", "payload": {"reason": "different"}}, format="json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.data["receipt"]["failure_code"], "IDEMPOTENCY_KEY_PAYLOAD_MISMATCH")

    def test_actions_activity_operation_and_integrity_endpoints_are_authorized(self):
        journey = self._journey()

        actions = self.client.get(f"/api/learning-journeys/{journey['journey_id']}/actions/")
        activity = self.client.get(f"/api/learning-journeys/{journey['journey_id']}/activity/")
        integrity = self.client.get(f"/api/learning-journeys/{journey['journey_id']}/integrity/")

        self.assertEqual(actions.status_code, 200)
        self.assertEqual(activity.status_code, 200)
        self.assertEqual(integrity.status_code, 200)
        self.assertIn("actions", actions.data)
        self.assertIn("activity", activity.data)
        self.assertIn("findings", integrity.data)

    def test_integrity_scan_records_open_finding_without_duplicates(self):
        journey = LearningJourney.objects.create(learner=self.learner, journey_type="SELF_STUDY", institution=self.institution)

        first = LearningJourneyIntegrityService().check(journey_id=journey.id, actor=self.learner)
        second = LearningJourneyIntegrityService().check(journey_id=journey.id, actor=self.learner)

        self.assertEqual(len(first["findings"]), len(second["findings"]))
        self.assertEqual(
            LearningJourneyIntegrityFinding.objects.filter(
                journey=journey,
                code=LearningJourneyIntegrityFindingCode.MISSING_SOURCE_BINDING,
                status=LearningJourneyIntegrityFindingStatus.OPEN,
            ).count(),
            1,
        )

    def test_other_learner_cannot_read_operational_detail(self):
        journey = self._journey()
        self.client.force_authenticate(self.other)

        response = self.client.get(f"/api/learning-journeys/{journey['journey_id']}/")

        self.assertEqual(response.status_code, 403)
