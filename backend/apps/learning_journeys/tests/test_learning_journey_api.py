from django.test import TestCase
from rest_framework.test import APIClient

from apps.learning_journeys.domain.enums import LearningJourneyStatus
from apps.self_study.workspace_models import SelfStudyWorkspace
from apps.users.models import Institution, InstitutionMembership, InstitutionRole, User


class LearningJourneyAPITests(TestCase):
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

    def test_create_list_retrieve_and_synchronize_self_study_journey(self):
        self.client.force_authenticate(self.learner)

        created = self.client.post("/api/learning-journeys/self-study/", {"workspace_id": str(self.workspace.id)}, format="json")
        self.assertEqual(created.status_code, 201)
        journey_id = created.data["journey_id"]
        self.assertEqual(created.data["state"], LearningJourneyStatus.DISCOVERING_GOAL)

        listed = self.client.get("/api/learning-journeys/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)

        retrieved = self.client.get(f"/api/learning-journeys/{journey_id}/")
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.data["current_step"]["code"], "DISCOVER_GOAL")

        synchronized = self.client.post(f"/api/learning-journeys/{journey_id}/synchronize/", {}, format="json")
        self.assertEqual(synchronized.status_code, 200)
        self.assertEqual(synchronized.data["state"], LearningJourneyStatus.DISCOVERING_GOAL)

    def test_duplicate_self_study_creation_returns_existing_journey(self):
        self.client.force_authenticate(self.learner)

        first = self.client.post("/api/learning-journeys/self-study/", {"workspace_id": str(self.workspace.id)}, format="json")
        second = self.client.post("/api/learning-journeys/self-study/", {"workspace_id": str(self.workspace.id)}, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data["journey_id"], second.data["journey_id"])

    def test_other_learner_cannot_create_or_read_workspace_journey(self):
        self.client.force_authenticate(self.other)

        response = self.client.post("/api/learning-journeys/self-study/", {"workspace_id": str(self.workspace.id)}, format="json")

        self.assertEqual(response.status_code, 403)

    def test_api_does_not_expose_arbitrary_status_mutation(self):
        self.client.force_authenticate(self.learner)
        created = self.client.post("/api/learning-journeys/self-study/", {"workspace_id": str(self.workspace.id)}, format="json")
        journey_id = created.data["journey_id"]

        response = self.client.patch(f"/api/learning-journeys/{journey_id}/", {"state": "LEARNING_ACTIVE"}, format="json")

        self.assertEqual(response.status_code, 405)
