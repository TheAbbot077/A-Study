from __future__ import annotations

from typing import Any, Optional

from django.utils import timezone

from apps.academic.domain.models import ContentConcept
from apps.core.exceptions import DomainValidationError, LifecycleTransitionError
from apps.assessments.domain.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentItem,
    AssessmentItemType,
    AssessmentResponse,
    AssessmentState,
)
from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import User


class AssessmentService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def create_assessment(
        self,
        content_concept: ContentConcept,
        title: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> Assessment:
        assessment = Assessment.objects.create(
            content_concept=content_concept,
            title=title,
            description=description,
            state=AssessmentState.CREATED,
            metadata=metadata or {},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.created",
                payload={
                    "assessment_id": str(assessment.id),
                    "content_concept_id": str(content_concept.id),
                    "state": assessment.state,
                },
            )
        )
        return assessment

    def add_item(
        self,
        assessment: Assessment,
        item_type: str,
        prompt: str,
        sequence_number: int,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AssessmentItem:
        if sequence_number < 1:
            raise DomainValidationError("Assessment item sequence_number must be greater than or equal to 1.")
        if item_type not in AssessmentItemType.values:
            raise DomainValidationError(f"Unsupported assessment item type: {item_type}.")

        item = AssessmentItem.objects.create(
            assessment=assessment,
            item_type=item_type,
            prompt=prompt,
            sequence_number=sequence_number,
            metadata=metadata or {},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.item_added",
                payload={
                    "assessment_id": str(assessment.id),
                    "item_id": str(item.id),
                    "item_type": item.item_type,
                    "sequence_number": item.sequence_number,
                },
            )
        )
        return item

    def start_attempt(
        self,
        assessment: Assessment,
        learner: User,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AssessmentAttempt:
        if assessment.state == AssessmentState.CREATED:
            assessment.state = AssessmentState.ACTIVE
            assessment.save()

        attempt = AssessmentAttempt.objects.create(
            assessment=assessment,
            learner=learner,
            state=AssessmentState.ACTIVE,
            metadata=metadata or {},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.attempt_started",
                payload={
                    "assessment_id": str(assessment.id),
                    "attempt_id": str(attempt.id),
                    "learner_id": str(learner.id),
                    "state": attempt.state,
                },
            )
        )
        return attempt

    def submit_response(
        self,
        attempt: AssessmentAttempt,
        item: AssessmentItem,
        response_data: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> AssessmentResponse:
        if attempt.state not in {AssessmentState.ACTIVE, AssessmentState.SUBMITTED}:
            raise LifecycleTransitionError(f"Cannot submit response while attempt is {attempt.state}.")

        response = AssessmentResponse.objects.create(
            attempt=attempt,
            item=item,
            response_data=response_data,
            metadata=metadata or {},
        )
        attempt.state = AssessmentState.SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.response_submitted",
                payload={
                    "assessment_id": str(attempt.assessment_id),
                    "attempt_id": str(attempt.id),
                    "item_id": str(item.id),
                    "response_id": str(response.id),
                    "state": attempt.state,
                },
            )
        )
        return response

    def complete_attempt(self, attempt: AssessmentAttempt) -> AssessmentAttempt:
        if attempt.state not in {AssessmentState.SUBMITTED, AssessmentState.EVALUATED}:
            raise LifecycleTransitionError(f"Cannot complete assessment attempt from {attempt.state}.")

        attempt.state = AssessmentState.COMPLETED
        attempt.completed_at = timezone.now()
        attempt.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.attempt_completed",
                payload={
                    "assessment_id": str(attempt.assessment_id),
                    "attempt_id": str(attempt.id),
                    "state": attempt.state,
                },
            )
        )
        return attempt

    def list_attempts(self, assessment: Assessment) -> list[AssessmentAttempt]:
        return list(AssessmentAttempt.objects.filter(assessment=assessment).order_by("-created_at"))

    def list_items(self, assessment: Assessment) -> list[AssessmentItem]:
        return list(AssessmentItem.objects.filter(assessment=assessment).order_by("sequence_number"))
