from __future__ import annotations

from apps.assessment_review.domain.models import (
    AssessmentReview,
    DifficultyCalibration,
    QualityFinding,
    QuestionReview,
    ReviewStatus,
    ReviewerAssignment,
    ReviewerAssignmentStatus,
    ReviewDecision,
)
from apps.assessments.domain.models import Assessment, ItemBankEntry
from apps.users.domain.models import User


class DjangoAssessmentReviewRepository:
    def add(self, review: AssessmentReview) -> AssessmentReview:
        review.save()
        return review

    def save(self, review: AssessmentReview) -> AssessmentReview:
        review.save()
        return review

    def get(self, review_id: str) -> AssessmentReview:
        return AssessmentReview.objects.get(id=review_id)

    def get_for_assessment(self, assessment: Assessment) -> AssessmentReview | None:
        return AssessmentReview.objects.filter(assessment=assessment).order_by("-created_at").first()

    def list_pending(self) -> list[AssessmentReview]:
        return list(AssessmentReview.objects.filter(status=ReviewStatus.PENDING_REVIEW).order_by("-created_at"))

    def list_for_assessment(self, assessment: Assessment) -> list[AssessmentReview]:
        return list(AssessmentReview.objects.filter(assessment=assessment).order_by("-created_at"))

    def list_for_reviewer(self, reviewer: User) -> list[AssessmentReview]:
        return list(AssessmentReview.objects.filter(reviewer=reviewer).order_by("-created_at"))


class DjangoQuestionReviewRepository:
    def add(self, review: QuestionReview) -> QuestionReview:
        review.save()
        return review

    def save(self, review: QuestionReview) -> QuestionReview:
        review.save()
        return review

    def get(self, review_id: str) -> QuestionReview:
        return QuestionReview.objects.get(id=review_id)

    def get_for_item(self, item_bank_entry: ItemBankEntry) -> QuestionReview | None:
        return QuestionReview.objects.filter(item_bank_entry=item_bank_entry).order_by("-created_at").first()

    def list_pending(self) -> list[QuestionReview]:
        return list(QuestionReview.objects.filter(status=ReviewStatus.PENDING_REVIEW).order_by("-created_at"))

    def list_for_item(self, item_bank_entry: ItemBankEntry) -> list[QuestionReview]:
        return list(QuestionReview.objects.filter(item_bank_entry=item_bank_entry).order_by("-created_at"))

    def list_for_reviewer(self, reviewer: User) -> list[QuestionReview]:
        return list(QuestionReview.objects.filter(reviewer=reviewer).order_by("-created_at"))


class DjangoQualityFindingRepository:
    def add(self, finding: QualityFinding) -> QualityFinding:
        finding.save()
        return finding

    def save(self, finding: QualityFinding) -> QualityFinding:
        finding.save()
        return finding

    def list_for_assessment_review(self, review: AssessmentReview) -> list[QualityFinding]:
        return list(QualityFinding.objects.filter(assessment_review=review).order_by("-created_at"))

    def list_for_question_review(self, review: QuestionReview) -> list[QualityFinding]:
        return list(QualityFinding.objects.filter(question_review=review).order_by("-created_at"))


class DjangoReviewDecisionRepository:
    def add(self, decision: ReviewDecision) -> ReviewDecision:
        decision.save()
        return decision

    def list_for_assessment_review(self, review: AssessmentReview) -> list[ReviewDecision]:
        return list(ReviewDecision.objects.filter(assessment_review=review).order_by("-decided_at"))

    def list_for_question_review(self, review: QuestionReview) -> list[ReviewDecision]:
        return list(ReviewDecision.objects.filter(question_review=review).order_by("-decided_at"))


class DjangoCalibrationRepository:
    def add(self, calibration: DifficultyCalibration) -> DifficultyCalibration:
        calibration.save()
        return calibration

    def list_for_assessment(self, assessment: Assessment) -> list[DifficultyCalibration]:
        return list(DifficultyCalibration.objects.filter(assessment=assessment).order_by("-created_at"))

    def list_for_item(self, item_bank_entry: ItemBankEntry) -> list[DifficultyCalibration]:
        return list(DifficultyCalibration.objects.filter(item_bank_entry=item_bank_entry).order_by("-created_at"))

    def list_recent(self, limit: int = 100) -> list[DifficultyCalibration]:
        return list(DifficultyCalibration.objects.order_by("-created_at")[:limit])


class DjangoReviewerAssignmentRepository:
    def add(self, assignment: ReviewerAssignment) -> ReviewerAssignment:
        assignment.save()
        return assignment

    def save(self, assignment: ReviewerAssignment) -> ReviewerAssignment:
        assignment.save()
        return assignment

    def list_for_reviewer(self, reviewer: User) -> list[ReviewerAssignment]:
        return list(ReviewerAssignment.objects.filter(reviewer=reviewer).order_by("-assigned_at"))

    def list_active_for_reviewer(self, reviewer: User) -> list[ReviewerAssignment]:
        return list(
            ReviewerAssignment.objects.filter(reviewer=reviewer)
            .exclude(status__in=[ReviewerAssignmentStatus.COMPLETED, ReviewerAssignmentStatus.CANCELLED])
            .order_by("-assigned_at")
        )

    def list_for_assessment_review(self, review: AssessmentReview) -> list[ReviewerAssignment]:
        return list(ReviewerAssignment.objects.filter(assessment_review=review).order_by("-assigned_at"))

    def list_for_question_review(self, review: QuestionReview) -> list[ReviewerAssignment]:
        return list(ReviewerAssignment.objects.filter(question_review=review).order_by("-assigned_at"))


__all__ = [
    "DjangoAssessmentReviewRepository",
    "DjangoQuestionReviewRepository",
    "DjangoQualityFindingRepository",
    "DjangoReviewDecisionRepository",
    "DjangoCalibrationRepository",
    "DjangoReviewerAssignmentRepository",
]
