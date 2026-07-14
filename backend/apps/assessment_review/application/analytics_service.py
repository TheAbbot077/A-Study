from __future__ import annotations

from collections import Counter
import logging

from apps.assessment_review.domain.models import AssessmentReview, QuestionReview, ReviewDecisionValue, ReviewStatus
from apps.assessments.domain.models import Assessment, AssessmentEvaluation, AssessmentItemBankLink, AssessmentResult, ItemBankEntry

logger = logging.getLogger(__name__)


class AssessmentAnalyticsService:
    def assessment_metrics(self, assessment: Assessment) -> dict:
        results = list(AssessmentResult.objects.filter(attempt__assessment=assessment))
        scores = [result.percentage for result in results if result.percentage is not None]
        passed = [result for result in results if result.passed is True]
        reviews = list(AssessmentReview.objects.filter(assessment=assessment))
        decisions = [decision.decision for review in reviews for decision in review.decisions.all()]
        completed_reviews = [review for review in reviews if review.completed_at and review.opened_at]
        pending_review_count = AssessmentReview.objects.filter(status=ReviewStatus.PENDING_REVIEW).count()

        return {
            "assessment_id": str(assessment.id),
            "attempt_count": len(results),
            "pass_rate": (len(passed) / len(results)) if results else None,
            "average_score": (sum(scores) / len(scores)) if scores else None,
            "approval_rate": self._rate(decisions, ReviewDecisionValue.APPROVED),
            "review_backlog": pending_review_count,
            "review_cycle_time_seconds": self._average_cycle_time(completed_reviews),
            "revision_frequency": self._rate(decisions, ReviewDecisionValue.NEEDS_REVISION),
        }

    def question_metrics(self, item_bank_entry: ItemBankEntry) -> dict:
        assessment_ids = AssessmentItemBankLink.objects.filter(item_bank_entry=item_bank_entry).values_list("assessment_id", flat=True)
        evaluations = list(AssessmentEvaluation.objects.filter(response__item__assessment_id__in=assessment_ids))
        correct = [evaluation for evaluation in evaluations if evaluation.is_correct is True]
        reviews = list(QuestionReview.objects.filter(item_bank_entry=item_bank_entry))
        if not assessment_ids:
            logger.info("Question review analytics requested for unlinked item bank entry: item_bank_entry_id=%s", item_bank_entry.id)

        return {
            "item_bank_entry_id": str(item_bank_entry.id),
            "question_success_rate": (len(correct) / len(evaluations)) if evaluations else None,
            "review_count": len(reviews),
            "difficulty_distribution": dict(Counter([item_bank_entry.difficulty])),
            "discrimination_metrics": {},
        }

    def platform_metrics(self) -> dict:
        pending_assessment_reviews = AssessmentReview.objects.filter(status=ReviewStatus.PENDING_REVIEW).count()
        pending_question_reviews = QuestionReview.objects.filter(status=ReviewStatus.PENDING_REVIEW).count()
        return {
            "pending_assessment_reviews": pending_assessment_reviews,
            "pending_question_reviews": pending_question_reviews,
            "review_backlog": pending_assessment_reviews + pending_question_reviews,
        }

    def _rate(self, values: list[str], target: str) -> float | None:
        if not values:
            return None
        return values.count(target) / len(values)

    def _average_cycle_time(self, reviews: list[AssessmentReview]) -> float | None:
        if not reviews:
            return None
        durations = [(review.completed_at - review.opened_at).total_seconds() for review in reviews]
        return sum(durations) / len(durations)
