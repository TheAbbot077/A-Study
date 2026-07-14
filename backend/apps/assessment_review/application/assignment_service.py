from __future__ import annotations

from typing import Optional

from apps.assessment_review.domain.models import AssessmentReview, QuestionReview, ReviewerAssignment
from apps.assessment_review.domain.repositories import ReviewerAssignmentRepository
from apps.assessment_review.infrastructure.persistence import DjangoReviewerAssignmentRepository
from apps.users.domain.models import User


class ReviewerAssignmentService:
    def __init__(self, assignment_repository: Optional[ReviewerAssignmentRepository] = None) -> None:
        self.assignment_repository = assignment_repository or DjangoReviewerAssignmentRepository()

    def assign_assessment_review(
        self,
        assessment_review: AssessmentReview,
        reviewer: User,
        metadata: dict | None = None,
    ) -> ReviewerAssignment:
        assessment_review.reviewer = reviewer
        return self.assignment_repository.add(
            ReviewerAssignment(assessment_review=assessment_review, reviewer=reviewer, metadata=metadata or {})
        )

    def assign_question_review(
        self,
        question_review: QuestionReview,
        reviewer: User,
        metadata: dict | None = None,
    ) -> ReviewerAssignment:
        question_review.reviewer = reviewer
        return self.assignment_repository.add(
            ReviewerAssignment(question_review=question_review, reviewer=reviewer, metadata=metadata or {})
        )

    def reassign(self, assignment: ReviewerAssignment, reviewer: User) -> ReviewerAssignment:
        assignment.reassign(reviewer)
        return self.assignment_repository.save(assignment)

    def complete_assignment(self, assignment: ReviewerAssignment) -> ReviewerAssignment:
        assignment.complete()
        return self.assignment_repository.save(assignment)

    def reviewer_workload(self, reviewer: User) -> dict:
        active = self.assignment_repository.list_active_for_reviewer(reviewer)
        return {"reviewer_id": str(reviewer.id), "active_assignment_count": len(active)}

    def reviewer_history(self, reviewer: User) -> list[ReviewerAssignment]:
        return self.assignment_repository.list_for_reviewer(reviewer)
