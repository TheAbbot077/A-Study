from __future__ import annotations

from typing import Optional

from apps.assessment_review.domain.models import (
    AssessmentReview,
    FindingSeverity,
    QualityFinding,
    ReviewDecision,
    ReviewDecisionValue,
    ReviewStatus,
)
from apps.assessment_review.domain.repositories import (
    AssessmentReviewRepository,
    QualityFindingRepository,
    ReviewDecisionRepository,
)
from apps.assessment_review.infrastructure.persistence import (
    DjangoAssessmentReviewRepository,
    DjangoQualityFindingRepository,
    DjangoReviewDecisionRepository,
)
from apps.assessments.domain.models import Assessment
from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import User


class AssessmentReviewService:
    def __init__(
        self,
        review_repository: Optional[AssessmentReviewRepository] = None,
        finding_repository: Optional[QualityFindingRepository] = None,
        decision_repository: Optional[ReviewDecisionRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.review_repository = review_repository or DjangoAssessmentReviewRepository()
        self.finding_repository = finding_repository or DjangoQualityFindingRepository()
        self.decision_repository = decision_repository or DjangoReviewDecisionRepository()
        self.event_publisher = event_publisher or EventPublisher()

    def open_review(
        self,
        assessment: Assessment,
        opened_by: User | None = None,
        reviewer: User | None = None,
        metadata: dict | None = None,
    ) -> AssessmentReview:
        review = AssessmentReview(assessment=assessment, opened_by=opened_by, reviewer=reviewer, metadata=metadata or {})
        review.transition_to(ReviewStatus.PENDING_REVIEW)
        return self.review_repository.add(review)

    def start_review(self, review: AssessmentReview, reviewer: User | None = None) -> AssessmentReview:
        if reviewer is not None:
            review.reviewer = reviewer
        review.transition_to(ReviewStatus.IN_REVIEW)
        review = self.review_repository.save(review)
        self._publish(
            "assessment_review.started",
            {"assessment_review_id": str(review.id), "assessment_id": str(review.assessment_id)},
        )
        return review

    def record_finding(
        self,
        review: AssessmentReview,
        finding_type: str,
        description: str,
        severity: str = FindingSeverity.MEDIUM,
        metadata: dict | None = None,
    ) -> QualityFinding:
        return self.finding_repository.add(
            QualityFinding(
                assessment_review=review,
                finding_type=finding_type,
                severity=severity,
                description=description,
                metadata=metadata or {},
            )
        )

    def record_decision(
        self,
        review: AssessmentReview,
        decision: str,
        decided_by: User | None = None,
        rationale: str = "",
        metadata: dict | None = None,
    ) -> ReviewDecision:
        if decision not in ReviewDecisionValue.values:
            raise ValueError(f"Unsupported assessment review decision: {decision}.")
        review.transition_to(decision)
        self.review_repository.save(review)
        decision_record = self.decision_repository.add(
            ReviewDecision(
                assessment_review=review,
                decision=decision,
                decided_by=decided_by,
                rationale=rationale,
                metadata=metadata or {},
            )
        )
        self._publish_decision_event(review, decision)
        return decision_record

    def approve_review(self, review: AssessmentReview, decided_by: User | None = None, rationale: str = "") -> ReviewDecision:
        return self.record_decision(review, ReviewDecisionValue.APPROVED, decided_by, rationale)

    def reject_review(self, review: AssessmentReview, decided_by: User | None = None, rationale: str = "") -> ReviewDecision:
        return self.record_decision(review, ReviewDecisionValue.REJECTED, decided_by, rationale)

    def request_revision(self, review: AssessmentReview, decided_by: User | None = None, rationale: str = "") -> ReviewDecision:
        return self.record_decision(review, ReviewDecisionValue.NEEDS_REVISION, decided_by, rationale)

    def list_pending_reviews(self) -> list[AssessmentReview]:
        return self.review_repository.list_pending()

    def _publish_decision_event(self, review: AssessmentReview, decision: str) -> None:
        event_names = {
            ReviewDecisionValue.APPROVED: "assessment_review.assessment_approved",
            ReviewDecisionValue.REJECTED: "assessment_review.assessment_rejected",
            ReviewDecisionValue.NEEDS_REVISION: "assessment_review.assessment_needs_revision",
        }
        event_name = event_names.get(decision)
        if event_name:
            self._publish(event_name, {"assessment_review_id": str(review.id), "assessment_id": str(review.assessment_id)})

    def _publish(self, event_name: str, payload: dict) -> None:
        self.event_publisher.publish(BusinessEvent.create(event_name, payload=payload))
