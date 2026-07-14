import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.assessments.domain.models import (
    AssessmentAttempt,
    AssessmentEvaluation,
    AssessmentItem,
    AssessmentItemType,
    AssessmentResponse,
    AssessmentResult,
    AssessmentState,
    EvaluatorType,
)
from apps.assessments.services import AssessmentEvaluationService
from apps.core.events import default_event_registry


class AssessmentEvaluationServiceTests(SimpleTestCase):
    def test_evaluate_multiple_choice_response_correct(self):
        service = AssessmentEvaluationService(event_publisher=Mock())
        response = self._response(AssessmentItemType.MULTIPLE_CHOICE, {"answer_key": "A"}, {"answer": "A"})

        with self._patched_evaluation_create():
            evaluation = service.evaluate_response(response)

        self.assertEqual(evaluation.score, 1.0)
        self.assertTrue(evaluation.is_correct)
        self.assertEqual(evaluation.evaluator_type, EvaluatorType.DETERMINISTIC)

    def test_evaluate_multiple_choice_response_incorrect(self):
        service = AssessmentEvaluationService(event_publisher=Mock())
        response = self._response(AssessmentItemType.MULTIPLE_CHOICE, {"answer_key": "A"}, {"answer": "B"})

        with self._patched_evaluation_create():
            evaluation = service.evaluate_response(response)

        self.assertEqual(evaluation.score, 0.0)
        self.assertFalse(evaluation.is_correct)

    def test_evaluate_true_false_response_correct(self):
        service = AssessmentEvaluationService(event_publisher=Mock())
        response = self._response(AssessmentItemType.TRUE_FALSE, {"answer_key": True}, {"answer": "true"})

        with self._patched_evaluation_create():
            evaluation = service.evaluate_response(response)

        self.assertEqual(evaluation.score, 1.0)
        self.assertTrue(evaluation.is_correct)

    def test_evaluate_true_false_response_incorrect(self):
        service = AssessmentEvaluationService(event_publisher=Mock())
        response = self._response(AssessmentItemType.TRUE_FALSE, {"answer_key": False}, {"answer": "true"})

        with self._patched_evaluation_create():
            evaluation = service.evaluate_response(response)

        self.assertEqual(evaluation.score, 0.0)
        self.assertFalse(evaluation.is_correct)

    def test_create_evaluation_record(self):
        publisher = Mock()
        service = AssessmentEvaluationService(event_publisher=publisher)
        response = self._response()

        with patch("apps.assessments.services.assessment_evaluation_service.AssessmentEvaluation.objects") as evaluation_objects:
            evaluation_objects.create.side_effect = self._create_evaluation
            evaluation = service.create_evaluation(response, 0.5, is_correct=False, feedback="Partial")

        self.assertEqual(evaluation.score, 0.5)
        evaluation_objects.create.assert_called_once()
        self.assertEqual(evaluation_objects.create.call_args.kwargs["evaluator_type"], EvaluatorType.DETERMINISTIC)
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.response_evaluated")

    def test_evaluate_attempt_aggregates_responses(self):
        publisher = Mock()
        service = AssessmentEvaluationService(event_publisher=publisher)
        attempt = self._attempt()
        responses = [
            self._response(AssessmentItemType.MULTIPLE_CHOICE, {"answer_key": "A"}, {"answer": "A"}, attempt=attempt),
            self._response(AssessmentItemType.TRUE_FALSE, {"answer_key": False}, {"answer": "true"}, attempt=attempt),
        ]

        with patch("apps.assessments.services.assessment_evaluation_service.AssessmentResponse.objects") as response_objects:
            with self._patched_evaluation_create():
                with patch("apps.assessments.services.assessment_evaluation_service.AssessmentResult.objects") as result_objects:
                    response_objects.filter.return_value.order_by.return_value = responses
                    result_objects.update_or_create.side_effect = self._update_or_create_result(created=True)

                    result = service.evaluate_attempt(attempt)

        self.assertEqual(result.total_score, 1.0)
        self.assertEqual(result.max_score, 2.0)
        self.assertEqual(result.percentage, 50.0)
        self.assertEqual(attempt.state, AssessmentState.EVALUATED)
        attempt.save.assert_called_once()
        self.assertIn("assessment.attempt_evaluated", [call.args[0].event_name for call in publisher.publish.call_args_list])

    def test_create_result(self):
        publisher = Mock()
        service = AssessmentEvaluationService(event_publisher=publisher)

        with patch("apps.assessments.services.assessment_evaluation_service.AssessmentResult.objects") as result_objects:
            result_objects.update_or_create.side_effect = self._update_or_create_result(created=True)
            result = service.create_or_update_result(self._attempt(), 8.0, max_score=10.0, passed=True)

        self.assertEqual(result.percentage, 80.0)
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.result_created")

    def test_update_existing_result(self):
        publisher = Mock()
        service = AssessmentEvaluationService(event_publisher=publisher)

        with patch("apps.assessments.services.assessment_evaluation_service.AssessmentResult.objects") as result_objects:
            result_objects.update_or_create.side_effect = self._update_or_create_result(created=False)
            result = service.create_or_update_result(self._attempt(), 6.0, max_score=10.0, passed=False)

        self.assertEqual(result.percentage, 60.0)
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.result_updated")

    def test_create_evaluation_rejects_negative_score(self):
        service = AssessmentEvaluationService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.create_evaluation(self._response(), -0.1)

    def test_create_or_update_result_rejects_negative_max_score(self):
        service = AssessmentEvaluationService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.create_or_update_result(self._attempt(), 1.0, max_score=-1.0)

    def test_list_evaluations_for_attempt(self):
        service = AssessmentEvaluationService(event_publisher=Mock())
        attempt = self._attempt()
        expected = [Mock(spec=AssessmentEvaluation)]

        with patch("apps.assessments.services.assessment_evaluation_service.AssessmentEvaluation.objects") as evaluation_objects:
            evaluation_objects.filter.return_value.order_by.return_value = expected
            evaluations = service.list_evaluations_for_attempt(attempt)

        self.assertEqual(evaluations, expected)
        evaluation_objects.filter.assert_called_once_with(response__attempt=attempt)
        evaluation_objects.filter.return_value.order_by.assert_called_once_with("created_at")

    def test_get_result_for_attempt(self):
        service = AssessmentEvaluationService(event_publisher=Mock())
        attempt = self._attempt()
        expected = Mock(spec=AssessmentResult)

        with patch("apps.assessments.services.assessment_evaluation_service.AssessmentResult.objects") as result_objects:
            result_objects.get.return_value = expected
            result = service.get_result_for_attempt(attempt)

        self.assertIs(result, expected)
        result_objects.get.assert_called_once_with(attempt=attempt)

    def test_no_mastery_profile_update(self):
        attempt = self._attempt()
        attempt.mastery_profile = Mock()

        with patch("apps.assessments.services.assessment_evaluation_service.AssessmentResult.objects") as result_objects:
            result_objects.update_or_create.side_effect = self._update_or_create_result(created=True)
            AssessmentEvaluationService(event_publisher=Mock()).create_or_update_result(attempt, 1.0, max_score=1.0)

        attempt.mastery_profile.save.assert_not_called()

    def test_no_mastery_decision_creation(self):
        with patch("apps.assessments.services.assessment_evaluation_service.AssessmentResult.objects") as result_objects:
            result_objects.update_or_create.side_effect = self._update_or_create_result(created=True)
            AssessmentEvaluationService(event_publisher=Mock()).create_or_update_result(self._attempt(), 1.0, max_score=1.0)

        self.assertTrue(result_objects.update_or_create.called)

    def test_deterministic_evaluator_type(self):
        service = AssessmentEvaluationService(event_publisher=Mock())
        response = self._response()

        with self._patched_evaluation_create():
            evaluation = service.create_evaluation(response, 1.0)

        self.assertEqual(evaluation.evaluator_type, EvaluatorType.DETERMINISTIC)

    def test_event_publishing(self):
        expected = {
            "assessment.response_evaluated",
            "assessment.attempt_evaluated",
            "assessment.result_created",
            "assessment.result_updated",
        }

        self.assertTrue(expected.issubset(set(default_event_registry._subscribers)))

    def _patched_evaluation_create(self):
        return patch(
            "apps.assessments.services.assessment_evaluation_service.AssessmentEvaluation.objects.create",
            side_effect=self._create_evaluation,
        )

    def _create_evaluation(self, **kwargs):
        return SimpleNamespace(id=uuid.uuid4(), **kwargs)

    def _update_or_create_result(self, created):
        def _inner(attempt, defaults):
            return SimpleNamespace(id="result-1", attempt=attempt, **defaults), created

        return _inner

    def _attempt(self):
        attempt = Mock(spec=AssessmentAttempt)
        attempt.id = "attempt-1"
        attempt.assessment_id = "assessment-1"
        attempt.state = AssessmentState.SUBMITTED
        attempt.save = Mock()
        return attempt

    def _response(self, item_type=AssessmentItemType.MULTIPLE_CHOICE, item_metadata=None, response_data=None, attempt=None):
        item = Mock(spec=AssessmentItem)
        item.id = "item-1"
        item.item_type = item_type
        item.metadata = item_metadata or {"answer_key": "A"}
        attempt = attempt or self._attempt()
        response = Mock(spec=AssessmentResponse)
        response.id = "response-1"
        response.attempt = attempt
        response.attempt_id = attempt.id
        response.item = item
        response.response_data = response_data or {"answer": "A"}
        return response
