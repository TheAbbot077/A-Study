from __future__ import annotations

from apps.core.events import BusinessEvent


class QuestionAuthoredReviewSubscriber:
    def __call__(self, event: BusinessEvent) -> None:
        return None


class AssessmentEvaluatedReviewSubscriber:
    def __call__(self, event: BusinessEvent) -> None:
        return None


class EvidenceIntegratedReviewSubscriber:
    def __call__(self, event: BusinessEvent) -> None:
        return None


class AssessmentPublishedReviewSubscriber:
    def __call__(self, event: BusinessEvent) -> None:
        return None
