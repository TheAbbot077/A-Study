from unittest.mock import Mock, patch

from django.db import models
from django.test import SimpleTestCase

from apps.assessments.domain.models import Assessment, AssessmentAttempt, AssessmentItem, AssessmentItemType, AssessmentResponse, AssessmentState
from apps.assessments.services import AssessmentService
from apps.core.events import default_event_registry


class DummyContentConcept:
    id = "concept-1"


class DummyLearner:
    id = "learner-1"


class AssessmentServiceTests(SimpleTestCase):
    def test_assessment_creation(self):
        publisher = Mock()
        service = AssessmentService(event_publisher=publisher)
        concept = DummyContentConcept()

        with patch("apps.assessments.services.assessment_service.Assessment.objects") as assessment_objects:
            fake_assessment = Mock(spec=Assessment)
            fake_assessment.id = "assessment-1"
            fake_assessment.state = AssessmentState.CREATED
            assessment_objects.create.return_value = fake_assessment

            assessment = service.create_assessment(concept, "Concept Check", "Check understanding")

        self.assertIs(assessment, fake_assessment)
        assessment_objects.create.assert_called_once_with(
            content_concept=concept,
            title="Concept Check",
            description="Check understanding",
            state=AssessmentState.CREATED,
            metadata={},
        )
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "assessment.created")

    def test_adding_items(self):
        publisher = Mock()
        service = AssessmentService(event_publisher=publisher)
        assessment = self._assessment()

        with patch("apps.assessments.services.assessment_service.AssessmentItem.objects") as item_objects:
            fake_item = Mock(spec=AssessmentItem)
            fake_item.id = "item-1"
            fake_item.item_type = AssessmentItemType.SHORT_ANSWER
            fake_item.sequence_number = 1
            item_objects.create.return_value = fake_item

            item = service.add_item(assessment, AssessmentItemType.SHORT_ANSWER, "Explain the idea.", 1)

        self.assertIs(item, fake_item)
        item_objects.create.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "assessment.item_added")
        self.assertEqual(event.payload["sequence_number"], 1)

    def test_starting_attempts(self):
        publisher = Mock()
        service = AssessmentService(event_publisher=publisher)
        assessment = self._assessment(state=AssessmentState.CREATED)
        learner = DummyLearner()

        with patch("apps.assessments.services.assessment_service.AssessmentAttempt.objects") as attempt_objects:
            fake_attempt = Mock(spec=AssessmentAttempt)
            fake_attempt.id = "attempt-1"
            fake_attempt.state = AssessmentState.ACTIVE
            attempt_objects.create.return_value = fake_attempt

            attempt = service.start_attempt(assessment, learner)

        self.assertIs(attempt, fake_attempt)
        self.assertEqual(assessment.state, AssessmentState.ACTIVE)
        assessment.save.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "assessment.attempt_started")

    def test_submitting_responses(self):
        publisher = Mock()
        service = AssessmentService(event_publisher=publisher)
        attempt = self._attempt(state=AssessmentState.ACTIVE)
        item = self._item()

        with patch("apps.assessments.services.assessment_service.AssessmentResponse.objects") as response_objects:
            fake_response = Mock(spec=AssessmentResponse)
            fake_response.id = "response-1"
            response_objects.create.return_value = fake_response

            response = service.submit_response(attempt, item, {"answer": "Opportunity cost"})

        self.assertIs(response, fake_response)
        self.assertEqual(attempt.state, AssessmentState.SUBMITTED)
        self.assertIsNotNone(attempt.submitted_at)
        attempt.save.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "assessment.response_submitted")

    def test_attempt_completion(self):
        publisher = Mock()
        service = AssessmentService(event_publisher=publisher)
        attempt = self._attempt(state=AssessmentState.SUBMITTED)

        completed_attempt = service.complete_attempt(attempt)

        self.assertIs(completed_attempt, attempt)
        self.assertEqual(attempt.state, AssessmentState.COMPLETED)
        self.assertIsNotNone(attempt.completed_at)
        attempt.save.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "assessment.attempt_completed")

    def test_state_transitions_reject_invalid_response_submission(self):
        service = AssessmentService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.submit_response(self._attempt(state=AssessmentState.COMPLETED), self._item(), {"answer": "x"})

    def test_state_transitions_reject_invalid_completion(self):
        service = AssessmentService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.complete_attempt(self._attempt(state=AssessmentState.ACTIVE))

    def test_ordering(self):
        service = AssessmentService(event_publisher=Mock())
        assessment = self._assessment()
        expected_items = [Mock(), Mock()]
        expected_attempts = [Mock()]

        with patch("apps.assessments.services.assessment_service.AssessmentItem.objects") as item_objects:
            item_objects.filter.return_value.order_by.return_value = expected_items
            items = service.list_items(assessment)

        with patch("apps.assessments.services.assessment_service.AssessmentAttempt.objects") as attempt_objects:
            attempt_objects.filter.return_value.order_by.return_value = expected_attempts
            attempts = service.list_attempts(assessment)

        self.assertEqual(items, expected_items)
        self.assertEqual(attempts, expected_attempts)
        item_objects.filter.return_value.order_by.assert_called_once_with("sequence_number")
        attempt_objects.filter.return_value.order_by.assert_called_once_with("-created_at")

    def test_event_publication_for_service_behaviour(self):
        expected_event_names = {
            "assessment.created",
            "assessment.item_added",
            "assessment.attempt_started",
            "assessment.response_submitted",
            "assessment.attempt_completed",
        }

        registered_event_names = set(default_event_registry._subscribers)

        self.assertTrue(expected_event_names.issubset(registered_event_names))

    def test_model_enums_and_constraints(self):
        self.assertEqual(
            {choice[0] for choice in AssessmentState.choices},
            {"created", "active", "submitted", "evaluated", "completed", "cancelled"},
        )
        self.assertEqual(
            {choice[0] for choice in AssessmentItemType.choices},
            {
                "multiple_choice",
                "short_answer",
                "essay",
                "calculation",
                "matching",
                "ordering",
                "true_false",
                "diagram",
                "oral",
                "teach_back",
                "programming",
                "clinical",
                "interview",
                "other",
            },
        )
        constraints = {constraint.name: constraint for constraint in AssessmentItem._meta.constraints}
        self.assertIsInstance(constraints["unique_assessment_item_sequence"], models.UniqueConstraint)
        self.assertEqual(AssessmentItem._meta.ordering, ["sequence_number"])

    def _assessment(self, state=AssessmentState.CREATED):
        assessment = Mock(spec=Assessment)
        assessment.id = "assessment-1"
        assessment.state = state
        assessment.save = Mock()
        return assessment

    def _attempt(self, state=AssessmentState.ACTIVE):
        attempt = Mock(spec=AssessmentAttempt)
        attempt.id = "attempt-1"
        attempt.assessment_id = "assessment-1"
        attempt.state = state
        attempt.submitted_at = None
        attempt.completed_at = None
        attempt.save = Mock()
        return attempt

    def _item(self):
        item = Mock(spec=AssessmentItem)
        item.id = "item-1"
        return item
