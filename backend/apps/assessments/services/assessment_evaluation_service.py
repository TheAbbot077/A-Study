from __future__ import annotations

from typing import Any, Optional

from apps.assessments.domain.models import (
    AssessmentAttempt,
    AssessmentEvaluation,
    AssessmentItemType,
    AssessmentResponse,
    AssessmentResult,
    AssessmentState,
    EvaluatorType,
)
from apps.core.exceptions import DomainValidationError, LifecycleTransitionError
from apps.core.events import BusinessEvent, EventPublisher


class AssessmentEvaluationService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def evaluate_response(self, response: AssessmentResponse) -> AssessmentEvaluation:
        score, is_correct, feedback, metadata = self._deterministic_score(response)
        evaluation = self.create_evaluation(
            response=response,
            score=score,
            is_correct=is_correct,
            feedback=feedback,
            metadata=metadata,
        )
        return evaluation

    def evaluate_attempt(self, attempt: AssessmentAttempt) -> AssessmentResult:
        if attempt.state not in {AssessmentState.ACTIVE, AssessmentState.SUBMITTED, AssessmentState.EVALUATED, AssessmentState.COMPLETED}:
            raise LifecycleTransitionError(f"Cannot evaluate assessment attempt from {attempt.state}.")
        responses = list(AssessmentResponse.objects.filter(attempt=attempt).order_by("submitted_at"))
        evaluations = [self.evaluate_response(response) for response in responses]
        total_score = sum(evaluation.score for evaluation in evaluations)
        max_score = sum(evaluation.max_score for evaluation in evaluations)
        passed = None if max_score == 0 else total_score >= (max_score * 0.7)
        result = self.create_or_update_result(
            attempt=attempt,
            score=total_score,
            max_score=max_score,
            passed=passed,
            metadata={"evaluation_ids": [str(evaluation.id) for evaluation in evaluations]},
        )
        attempt.state = AssessmentState.EVALUATED
        attempt.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.attempt_evaluated",
                payload={
                    "attempt_id": str(attempt.id),
                    "assessment_id": str(attempt.assessment_id),
                    "total_score": result.total_score,
                    "max_score": result.max_score,
                    "percentage": result.percentage,
                },
            )
        )
        return result

    def create_evaluation(
        self,
        response: AssessmentResponse,
        score: float,
        is_correct: Optional[bool] = None,
        feedback: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AssessmentEvaluation:
        if score < 0:
            raise DomainValidationError("Assessment evaluation score must be greater than or equal to 0.")
        evaluation = AssessmentEvaluation.objects.create(
            response=response,
            score=score,
            max_score=1.0,
            is_correct=is_correct,
            feedback=feedback or "",
            evaluator_type=EvaluatorType.DETERMINISTIC,
            evaluation_data=metadata or {},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.response_evaluated",
                payload={
                    "response_id": str(response.id),
                    "attempt_id": str(response.attempt_id),
                    "evaluation_id": str(evaluation.id),
                    "score": evaluation.score,
                    "max_score": evaluation.max_score,
                    "is_correct": evaluation.is_correct,
                    "evaluator_type": evaluation.evaluator_type,
                },
            )
        )
        return evaluation

    def create_or_update_result(
        self,
        attempt: AssessmentAttempt,
        score: float,
        max_score: Optional[float] = None,
        passed: Optional[bool] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AssessmentResult:
        resolved_max_score = max_score if max_score is not None else 1.0
        if resolved_max_score < 0:
            raise DomainValidationError("Assessment result max_score must be greater than or equal to 0.")
        if score < 0:
            raise DomainValidationError("Assessment result total_score must be greater than or equal to 0.")
        percentage = None if resolved_max_score == 0 else round((score / resolved_max_score) * 100, 4)
        defaults = {
            "total_score": score,
            "max_score": resolved_max_score,
            "percentage": percentage,
            "passed": passed,
            "result_data": metadata or {},
        }
        result, created = AssessmentResult.objects.update_or_create(attempt=attempt, defaults=defaults)
        event_name = "assessment.result_created" if created else "assessment.result_updated"
        self.event_publisher.publish(
            BusinessEvent.create(
                event_name,
                payload={
                    "attempt_id": str(attempt.id),
                    "assessment_id": str(attempt.assessment_id),
                    "result_id": str(result.id),
                    "total_score": result.total_score,
                    "max_score": result.max_score,
                    "percentage": result.percentage,
                    "passed": result.passed,
                },
            )
        )
        return result

    def list_evaluations_for_attempt(self, attempt: AssessmentAttempt) -> list[AssessmentEvaluation]:
        return list(AssessmentEvaluation.objects.filter(response__attempt=attempt).order_by("created_at"))

    def get_result_for_attempt(self, attempt: AssessmentAttempt) -> AssessmentResult:
        return AssessmentResult.objects.get(attempt=attempt)

    def _deterministic_score(self, response: AssessmentResponse) -> tuple[float, Optional[bool], str, dict[str, Any]]:
        item_type = response.item.item_type
        answer_key = self._answer_key(response)
        if answer_key is None:
            return 0.0, None, "No deterministic answer key is available for this response.", {"reason": "missing_answer_key"}

        submitted_answer = self._submitted_answer(response)
        if item_type == AssessmentItemType.TRUE_FALSE:
            is_correct = self._normalize_bool(submitted_answer) == self._normalize_bool(answer_key)
        elif item_type == AssessmentItemType.MULTIPLE_CHOICE:
            is_correct = str(submitted_answer).strip() == str(answer_key).strip()
        else:
            return (
                0.0,
                None,
                f"Deterministic grading is not supported for item type {item_type}.",
                {"reason": "unsupported_item_type", "item_type": item_type},
            )

        score = 1.0 if is_correct else 0.0
        feedback = "Correct response." if is_correct else "Incorrect response."
        return score, is_correct, feedback, {"answer_key": answer_key, "submitted_answer": submitted_answer}

    def _answer_key(self, response: AssessmentResponse) -> Any:
        metadata = response.item.metadata or {}
        for key in ("answer_key", "correct_answer", "correct_option", "correct_value"):
            if key in metadata:
                return metadata[key]
        return None

    def _submitted_answer(self, response: AssessmentResponse) -> Any:
        response_data = response.response_data or {}
        for key in ("answer", "selected_option", "selected", "value"):
            if key in response_data:
                return response_data[key]
        return response_data

    def _normalize_bool(self, value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "t", "yes", "y", "1"}:
                return True
            if normalized in {"false", "f", "no", "n", "0"}:
                return False
        if isinstance(value, int) and value in {0, 1}:
            return bool(value)
        return None
