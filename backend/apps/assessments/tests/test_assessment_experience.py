from unittest.mock import Mock

from django.test import TestCase

from apps.assessments.api.serializers import AssessmentExperienceProductStateSerializer
from apps.assessments.domain.models import AssessmentExperience, AssessmentPurpose
from apps.assessments.services.assessment_experience_service import AssessmentExperienceService


class AssessmentExperienceTests(TestCase):
    def setUp(self):
        self.service = AssessmentExperienceService(event_publisher=Mock())

    def test_product_state_projection(self):
        experience = Mock(spec=AssessmentExperience)
        experience.id = "exp-1"
        experience.purpose = AssessmentPurpose.CONCEPT_CHECK
        experience.state = "awaiting_response"
        experience.current_step = {"code": "RESPOND", "title": "Answer the question"}
        experience.blockers = []
        experience.attempt_number = 1
        experience.feedback_available = False
        payload = self.service.get_product_state(experience)
        self.assertEqual(payload["status"], "AWAITING_RESPONSE")
        self.assertIn("SUBMIT_RESPONSE", payload["available_actions"])
        serialized = AssessmentExperienceProductStateSerializer(payload).data
        self.assertEqual(serialized["experience_id"], "exp-1")
