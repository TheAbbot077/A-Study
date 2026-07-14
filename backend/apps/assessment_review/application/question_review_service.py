from __future__ import annotations

from typing import Optional

from apps.assessment_review.domain.models import (
    FindingSeverity,
    QualityFinding,
    QuestionReview,
    ReviewDecision,
    ReviewDecisionValue,
    ReviewStatus,
)
from apps.assessment_review.domain.repositories import (
    QualityFindingRepository,
    QuestionReviewRepository,
    ReviewDecisionRepository,
)
from apps.assessment_review.infrastructure.persistence import (
    DjangoQualityFindingRepository,
    DjangoQuestionReviewRepository,
    DjangoReviewDecisionRepository,
)
from apps.assessments.domain.models import ItemBankEntry
from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import User


class QuestionReviewService:
    def __init__(
        self,
        review_repository: Optional[QuestionReviewRepository] = None,
        finding_repository: Optional[QualityFindingRepository] = None,
        decision_repository: Optional[ReviewDecisionRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.review_repository = review_repository or DjangoQuestionReviewRepository()
        self.finding_repository = finding_repository or DjangoQualityFindingRepository()
        self.decision_repository = decision_repository or DjangoReviewDecisionRepository()
        self.event_publisher = event_publisher or EventPublisher()

    def open_review(
        self,
        item_bank_entry: ItemBankEntry,
        opened_by: User | None = None,
        reviewer: User | None = None,
        metadata: dict | None = None,
    ) -> QuestionReview:
        review = QuestionReview(item_bank_entry=item_bank_entry, opened_by=opened_by, reviewer=reviewer, metadata=metadata or {})
        review.transition_to(ReviewStatus.PENDING_REVIEW)
        return self.review_repository.add(review)

    def start_review(self, review: QuestionReview, reviewer: User | None = None) -> QuestionReview:
        if reviewer is not None:
            review.reviewer = reviewer
        review.transition_to(ReviewStatus.IN_REVIEW)
        return self.review_repository.save(review)

    def record_finding(
        self,
        review: QuestionReview,
        finding_type: str,
        description: str,
        severity: str = FindingSeverity.MEDIUM,
        metadata: dict | None = None,
    ) -> QualityFinding:
        return self.finding_repository.add(
            QualityFinding(
                question_review=review,
                finding_type=finding_type,
                severity=severity,
                description=description,
                metadata=metadata or {},
            )
        )

    def record_decision(
        self,
        review: QuestionReview,
        decision: str,
        decided_by: User | None = None,
        rationale: str = "",
        metadata: dict | None = None,
    ) -> ReviewDecision:
        if decision not in ReviewDecisionValue.values:
            raise ValueError(f"Unsupported question review decision: {decision}.")
        review.transition_to(decision)
        self.review_repository.save(review)
        decision_record = self.decision_repository.add(
            ReviewDecision(
                question_review=review,
                decision=decision,
                decided_by=decided_by,
                rationale=rationale,
                metadata=metadata or {},
            )
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment_review.question_reviewed",
                payload={
                    "question_review_id": str(review.id),
                    "item_bank_entry_id": str(review.item_bank_entry_id),
                    "decision": decision,
                },
            )
        )
        return decision_record

    def list_pending_reviews(self) -> list[QuestionReview]:
        return self.review_repository.list_pending()
