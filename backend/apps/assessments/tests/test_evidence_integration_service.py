from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.assessments.domain.models import (
    AssessmentState,
    LearningEvidence,
    LearningEvidenceSourceType,
    LearningEvidenceType,
)
from apps.assessments.services import EvidenceIntegrationService
from apps.core.events import default_event_registry


class EvidenceIntegrationServiceTests(SimpleTestCase):
    def test_integrate_evaluation_into_learning_evidence(self):
        evidence_service = Mock()
        evidence_service.record_evidence.return_value = self._evidence()
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=evidence_service)
        evaluation = self._evaluation(score=1.0, max_score=1.0, is_correct=True)

        with self._no_existing_evidence():
            evidence = service.integrate_evaluation(evaluation)

        self.assertIs(evidence, evidence_service.record_evidence.return_value)
        evidence_service.record_evidence.assert_called_once()

    def test_integrate_result_into_learning_evidence(self):
        evidence_service = Mock()
        evidence_service.record_evidence.return_value = self._evidence()
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=evidence_service)
        result = self._result(percentage=85.0, passed=True)

        with self._no_existing_evidence():
            service.integrate_result(result)

        self.assertEqual(evidence_service.record_evidence.call_args.kwargs["source_type"], LearningEvidenceSourceType.ASSESSMENT_RESULT)
        self.assertEqual(evidence_service.record_evidence.call_args.kwargs["evidence_type"], LearningEvidenceType.COMPLETION)

    def test_integrate_attempt_with_multiple_evaluations(self):
        evidence_service = Mock()
        evidence_service.record_evidence.side_effect = [self._evidence("e1"), self._evidence("e2")]
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=evidence_service)
        attempt = self._attempt(state=AssessmentState.EVALUATED)
        evaluations = [self._evaluation("eval-1", attempt=attempt), self._evaluation("eval-2", attempt=attempt)]

        with self._no_existing_evidence():
            with patch("apps.assessments.services.evidence_integration_service.AssessmentEvaluation.objects") as evaluation_objects:
                with patch("apps.assessments.services.evidence_integration_service.AssessmentResult.objects") as result_objects:
                    evaluation_objects.filter.return_value.order_by.return_value = evaluations
                    result_objects.filter.return_value.first.return_value = None
                    summary = service.integrate_attempt(attempt)

        self.assertEqual(len(summary.integrated_evidence), 2)
        self.assertTrue(summary.mastery_reevaluation_recommended)

    def test_integrate_completed_attempt_only_when_allowed(self):
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=Mock())

        with patch.object(service, "integrate_attempt", return_value=Mock()) as integrate_attempt:
            service.integrate_completed_attempt(self._attempt(state=AssessmentState.SUBMITTED))
            service.integrate_completed_attempt(self._attempt(state=AssessmentState.EVALUATED))
            service.integrate_completed_attempt(self._attempt(state=AssessmentState.COMPLETED))

        self.assertEqual(integrate_attempt.call_count, 3)

    def test_integrate_completed_attempt_rejects_unfinished_state(self):
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=Mock())

        with self.assertRaises(ValueError):
            service.integrate_completed_attempt(self._attempt(state=AssessmentState.ACTIVE))

    def test_evidence_source_type_and_source_id_preserved(self):
        evidence_service = Mock()
        evidence_service.record_evidence.return_value = self._evidence()
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=evidence_service)
        evaluation = self._evaluation("evaluation-42")

        with self._no_existing_evidence():
            service.integrate_evaluation(evaluation)

        self.assertEqual(evidence_service.record_evidence.call_args.kwargs["source_type"], LearningEvidenceSourceType.ASSESSMENT_EVALUATION)
        self.assertEqual(evidence_service.record_evidence.call_args.kwargs["source_id"], "evaluation-42")

    def test_evidence_metadata_preserves_provenance(self):
        evidence_service = Mock()
        evidence_service.record_evidence.return_value = self._evidence()
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=evidence_service)
        result = self._result("result-42")

        with self._no_existing_evidence():
            service.integrate_result(result)

        metadata = evidence_service.record_evidence.call_args.kwargs["metadata"]

        self.assertEqual(metadata["provenance"], "assessment_result")
        self.assertEqual(metadata["result_id"], "result-42")
        self.assertEqual(metadata["attempt_id"], "attempt-1")

    def test_idempotency_prevents_duplicate_evidence(self):
        existing = self._evidence("existing")
        evidence_service = Mock()
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=evidence_service)

        with patch("apps.assessments.services.evidence_integration_service.LearningEvidence.objects") as evidence_objects:
            evidence_objects.filter.return_value.first.return_value = existing
            evidence = service.integrate_evaluation(self._evaluation())

        self.assertIs(evidence, existing)
        evidence_service.record_evidence.assert_not_called()

    def test_correct_response_maps_to_correct_response_evidence(self):
        self._assert_evaluation_maps(score=1.0, max_score=1.0, is_correct=True, expected=LearningEvidenceType.CORRECT_RESPONSE)

    def test_partial_score_maps_to_partial_understanding_evidence(self):
        self._assert_evaluation_maps(score=0.5, max_score=1.0, is_correct=None, expected=LearningEvidenceType.PARTIAL_UNDERSTANDING)

    def test_incorrect_response_maps_to_misconception_evidence(self):
        self._assert_evaluation_maps(score=0.0, max_score=1.0, is_correct=False, expected=LearningEvidenceType.MISCONCEPTION)

    def test_high_percentage_result_maps_to_strong_positive_evidence(self):
        evidence_service = Mock()
        evidence_service.record_evidence.return_value = self._evidence()
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=evidence_service)

        with self._no_existing_evidence():
            service.integrate_result(self._result(percentage=92.0, passed=True))

        self.assertEqual(evidence_service.record_evidence.call_args.kwargs["evidence_type"], LearningEvidenceType.COMPLETION)
        self.assertGreaterEqual(evidence_service.record_evidence.call_args.kwargs["confidence"], 0.9)

    def test_low_percentage_result_maps_to_weak_negative_evidence(self):
        evidence_service = Mock()
        evidence_service.record_evidence.return_value = self._evidence()
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=evidence_service)

        with self._no_existing_evidence():
            service.integrate_result(self._result(percentage=25.0, passed=False))

        self.assertEqual(evidence_service.record_evidence.call_args.kwargs["evidence_type"], LearningEvidenceType.MISCONCEPTION)

    def test_does_not_update_mastery_profile_automatically(self):
        attempt = self._attempt()
        attempt.mastery_profile = Mock()
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=Mock())

        with patch.object(service, "integrate_attempt", return_value=Mock()):
            service.integrate_completed_attempt(attempt)

        attempt.mastery_profile.save.assert_not_called()

    def test_does_not_unlock_progression(self):
        attempt = self._attempt()
        attempt.progression = Mock()
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=Mock())

        with patch.object(service, "integrate_attempt", return_value=Mock()):
            service.integrate_completed_attempt(attempt)

        attempt.progression.save.assert_not_called()

    def test_event_publishing(self):
        expected = {
            "assessment.evaluation_integrated_as_evidence",
            "assessment.result_integrated_as_evidence",
            "assessment.attempt_integrated_as_evidence",
        }

        self.assertTrue(expected.issubset(set(default_event_registry._subscribers)))

    def _assert_evaluation_maps(self, score, max_score, is_correct, expected):
        evidence_service = Mock()
        evidence_service.record_evidence.return_value = self._evidence()
        service = EvidenceIntegrationService(event_publisher=Mock(), evidence_service=evidence_service)

        with self._no_existing_evidence():
            service.integrate_evaluation(self._evaluation(score=score, max_score=max_score, is_correct=is_correct))

        self.assertEqual(evidence_service.record_evidence.call_args.kwargs["evidence_type"], expected)

    @contextmanager
    def _no_existing_evidence(self):
        with patch("apps.assessments.services.evidence_integration_service.LearningEvidence.objects") as patched:
            patched.filter.return_value.first.return_value = None
            yield patched

    def _attempt(self, state=AssessmentState.EVALUATED):
        learner = SimpleNamespace(id="learner-1")
        concept = SimpleNamespace(id="concept-1")
        assessment = SimpleNamespace(id="assessment-1", content_concept=concept)
        return SimpleNamespace(
            id="attempt-1",
            assessment_id="assessment-1",
            assessment=assessment,
            learner=learner,
            state=state,
        )

    def _evaluation(self, id="evaluation-1", score=1.0, max_score=1.0, is_correct=True, attempt=None):
        attempt = attempt or self._attempt()
        response = SimpleNamespace(id="response-1", attempt=attempt)
        return SimpleNamespace(
            id=id,
            response=response,
            score=score,
            max_score=max_score,
            is_correct=is_correct,
            evaluator_type="deterministic",
        )

    def _result(self, id="result-1", percentage=80.0, passed=True):
        return SimpleNamespace(
            id=id,
            attempt=self._attempt(),
            total_score=8.0,
            max_score=10.0,
            percentage=percentage,
            passed=passed,
        )

    def _evidence(self, id="evidence-1"):
        return Mock(spec=LearningEvidence, id=id)
