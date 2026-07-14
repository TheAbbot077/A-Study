from django.apps import AppConfig


class AssessmentReviewConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.assessment_review"
    verbose_name = "Assessment Review"

    def ready(self) -> None:
        from apps.assessment_review.infrastructure.events import (
            AssessmentEvaluatedReviewSubscriber,
            AssessmentPublishedReviewSubscriber,
            EvidenceIntegratedReviewSubscriber,
            QuestionAuthoredReviewSubscriber,
        )
        from apps.core.events import default_event_registry

        def subscribe_once(event_name: str, subscriber) -> None:
            existing = default_event_registry.get_subscribers(event_name)
            if any(type(item) is type(subscriber) for item in existing):
                return
            default_event_registry.subscribe(event_name, subscriber)

        subscribe_once("assessment.item_bank_entry_created", QuestionAuthoredReviewSubscriber())
        subscribe_once("assessment.attempt_evaluated", AssessmentEvaluatedReviewSubscriber())
        subscribe_once("assessment.evaluation_integrated_as_evidence", EvidenceIntegratedReviewSubscriber())
        subscribe_once("assessment.result_integrated_as_evidence", EvidenceIntegratedReviewSubscriber())
        subscribe_once("assessment.item_added_to_assessment", AssessmentPublishedReviewSubscriber())
