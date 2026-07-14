from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Optional

from apps.assessments.domain.models import (
    AssessmentAttempt,
    AssessmentEvaluation,
    AssessmentResult,
    AssessmentState,
    LearningEvidence,
    LearningEvidenceSourceType,
    LearningEvidenceType,
)
from apps.assessments.services.evidence_service import EvidenceService
from apps.core.exceptions import LifecycleTransitionError
from apps.core.events import BusinessEvent, EventPublisher

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvidenceIntegrationSummary:
    integrated_evidence: list[LearningEvidence]
    mastery_reevaluation_recommended: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class EvidenceIntegrationService:
    ALLOWED_COMPLETED_ATTEMPT_STATES = {
        AssessmentState.SUBMITTED,
        AssessmentState.EVALUATED,
        AssessmentState.COMPLETED,
    }

    def __init__(
        self,
        event_publisher: Optional[EventPublisher] = None,
        evidence_service: Optional[EvidenceService] = None,
    ) -> None:
        self.event_publisher = event_publisher or EventPublisher()
        self.evidence_service = evidence_service or EvidenceService(event_publisher=self.event_publisher)

    def integrate_evaluation(self, evaluation: AssessmentEvaluation) -> LearningEvidence:
        source_type = LearningEvidenceSourceType.ASSESSMENT_EVALUATION
        source_id = str(evaluation.id)
        existing = self._existing_evidence(source_type, source_id)
        if existing:
            logger.info("Assessment evaluation already integrated as learning evidence: evaluation_id=%s evidence_id=%s", evaluation.id, existing.id)
            self._publish_evaluation_event(evaluation, existing, created=False)
            return existing

        evidence_type, score, confidence = self._map_evaluation(evaluation)
        evidence = self.evidence_service.record_evidence(
            learner=evaluation.response.attempt.learner,
            content_concept=evaluation.response.attempt.assessment.content_concept,
            source_type=source_type,
            source_id=source_id,
            evidence_type=evidence_type,
            score=score,
            confidence=confidence,
            metadata={
                "provenance": "assessment_evaluation",
                "evaluation_id": str(evaluation.id),
                "response_id": str(evaluation.response.id),
                "attempt_id": str(evaluation.response.attempt.id),
                "assessment_id": str(evaluation.response.attempt.assessment.id),
                "score": evaluation.score,
                "max_score": evaluation.max_score,
                "is_correct": evaluation.is_correct,
                "evaluator_type": evaluation.evaluator_type,
            },
        )
        self._publish_evaluation_event(evaluation, evidence, created=True)
        return evidence

    def integrate_result(self, result: AssessmentResult) -> LearningEvidence:
        source_type = LearningEvidenceSourceType.ASSESSMENT_RESULT
        source_id = str(result.id)
        existing = self._existing_evidence(source_type, source_id)
        if existing:
            logger.info("Assessment result already integrated as learning evidence: result_id=%s evidence_id=%s", result.id, existing.id)
            self._publish_result_event(result, existing, created=False)
            return existing

        evidence_type, score, confidence = self._map_result(result)
        evidence = self.evidence_service.record_evidence(
            learner=result.attempt.learner,
            content_concept=result.attempt.assessment.content_concept,
            source_type=source_type,
            source_id=source_id,
            evidence_type=evidence_type,
            score=score,
            confidence=confidence,
            metadata={
                "provenance": "assessment_result",
                "result_id": str(result.id),
                "attempt_id": str(result.attempt.id),
                "assessment_id": str(result.attempt.assessment.id),
                "total_score": result.total_score,
                "max_score": result.max_score,
                "percentage": result.percentage,
                "passed": result.passed,
            },
        )
        self._publish_result_event(result, evidence, created=True)
        return evidence

    def integrate_attempt(self, attempt: AssessmentAttempt) -> EvidenceIntegrationSummary:
        integrated_evidence: list[LearningEvidence] = []
        evaluations = AssessmentEvaluation.objects.filter(response__attempt=attempt).order_by("created_at")
        for evaluation in evaluations:
            integrated_evidence.append(self.integrate_evaluation(evaluation))

        result = AssessmentResult.objects.filter(attempt=attempt).first()
        if result:
            integrated_evidence.append(self.integrate_result(result))

        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.attempt_integrated_as_evidence",
                payload={
                    "attempt_id": str(attempt.id),
                    "assessment_id": str(attempt.assessment_id),
                    "evidence_count": len(integrated_evidence),
                    "mastery_reevaluation_recommended": True,
                },
            )
        )
        return EvidenceIntegrationSummary(
            integrated_evidence=integrated_evidence,
            metadata={"attempt_id": str(attempt.id), "assessment_id": str(attempt.assessment_id)},
        )

    def integrate_completed_attempt(self, attempt: AssessmentAttempt) -> EvidenceIntegrationSummary:
        if attempt.state not in self.ALLOWED_COMPLETED_ATTEMPT_STATES:
            raise LifecycleTransitionError(f"Cannot integrate evidence for assessment attempt in state {attempt.state}.")
        return self.integrate_attempt(attempt)

    def list_integrated_evidence_for_attempt(self, attempt: AssessmentAttempt) -> list[LearningEvidence]:
        source_ids = [str(evaluation.id) for evaluation in AssessmentEvaluation.objects.filter(response__attempt=attempt)]
        result = AssessmentResult.objects.filter(attempt=attempt).first()
        if result:
            source_ids.append(str(result.id))
        if not source_ids:
            return []
        return list(
            LearningEvidence.objects.filter(
                source_type__in=[
                    LearningEvidenceSourceType.ASSESSMENT_EVALUATION,
                    LearningEvidenceSourceType.ASSESSMENT_RESULT,
                ],
                source_id__in=source_ids,
            ).order_by("-created_at")
        )

    def _existing_evidence(self, source_type: str, source_id: str) -> LearningEvidence | None:
        return LearningEvidence.objects.filter(source_type=source_type, source_id=source_id).first()

    def _map_evaluation(self, evaluation: AssessmentEvaluation) -> tuple[str, float | None, float]:
        ratio = self._score_ratio(evaluation.score, evaluation.max_score)
        if evaluation.is_correct is True:
            return LearningEvidenceType.CORRECT_RESPONSE, ratio, max(ratio, 0.8)
        if 0.0 < ratio < 1.0:
            return LearningEvidenceType.PARTIAL_UNDERSTANDING, ratio, ratio
        if evaluation.is_correct is False:
            return LearningEvidenceType.MISCONCEPTION, ratio, max(1.0 - ratio, 0.7)
        return LearningEvidenceType.OTHER, ratio, ratio

    def _map_result(self, result: AssessmentResult) -> tuple[str, float | None, float]:
        ratio = self._percentage_ratio(result.percentage)
        if result.passed is True:
            return LearningEvidenceType.COMPLETION, ratio, max(ratio, 0.75)
        if result.passed is False and ratio < 0.4:
            return LearningEvidenceType.MISCONCEPTION, ratio, max(1.0 - ratio, 0.7)
        if ratio >= 0.7:
            return LearningEvidenceType.COMPLETION, ratio, ratio
        return LearningEvidenceType.PARTIAL_UNDERSTANDING, ratio, max(ratio, 0.4)

    def _score_ratio(self, score: float, max_score: float) -> float:
        if max_score <= 0:
            return 0.0
        return self._clamp(score / max_score)

    def _percentage_ratio(self, percentage: float | None) -> float:
        if percentage is None:
            return 0.0
        return self._clamp(percentage / 100)

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, value)), 4)

    def _publish_evaluation_event(self, evaluation: AssessmentEvaluation, evidence: LearningEvidence, created: bool) -> None:
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.evaluation_integrated_as_evidence",
                payload={
                    "evaluation_id": str(evaluation.id),
                    "response_id": str(evaluation.response.id),
                    "attempt_id": str(evaluation.response.attempt.id),
                    "learning_evidence_id": str(evidence.id),
                    "created": created,
                },
            )
        )

    def _publish_result_event(self, result: AssessmentResult, evidence: LearningEvidence, created: bool) -> None:
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.result_integrated_as_evidence",
                payload={
                    "result_id": str(result.id),
                    "attempt_id": str(result.attempt.id),
                    "learning_evidence_id": str(evidence.id),
                    "created": created,
                },
            )
        )
