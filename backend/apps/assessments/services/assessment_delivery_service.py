from __future__ import annotations

from typing import Any, Optional
import logging

from django.utils import timezone

from apps.core.exceptions import DomainValidationError, LifecycleTransitionError
from apps.assessments.domain.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentDeliveryItem,
    AssessmentDeliverySession,
    AssessmentDeliveryState,
    AssessmentItem,
    AssessmentItemBankLink,
    AssessmentResponse,
    AssessmentState,
)
from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import User

logger = logging.getLogger(__name__)


class AssessmentDeliveryService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def create_delivery_session(
        self,
        assessment: Assessment,
        learner: User,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AssessmentDeliverySession:
        attempt = AssessmentAttempt.objects.create(
            assessment=assessment,
            learner=learner,
            state=AssessmentState.CREATED,
            metadata={"source": "assessment_delivery_service"},
        )
        delivery_session = AssessmentDeliverySession.objects.create(
            assessment=assessment,
            learner=learner,
            assessment_attempt=attempt,
            status=AssessmentDeliveryState.CREATED,
            current_sequence_number=1,
            metadata=metadata or {},
        )
        self._publish_session_event("assessment.delivery_session_created", delivery_session)
        return delivery_session

    def start_delivery_session(self, delivery_session: AssessmentDeliverySession) -> AssessmentDeliverySession:
        if delivery_session.status not in {AssessmentDeliveryState.CREATED, AssessmentDeliveryState.PAUSED, AssessmentDeliveryState.ACTIVE}:
            raise LifecycleTransitionError(f"Cannot start delivery session from {delivery_session.status}.")
        delivery_session.status = AssessmentDeliveryState.ACTIVE
        delivery_session.started_at = delivery_session.started_at or timezone.now()
        if delivery_session.assessment_attempt:
            delivery_session.assessment_attempt.state = AssessmentState.ACTIVE
            delivery_session.assessment_attempt.started_at = delivery_session.assessment_attempt.started_at or timezone.now()
            delivery_session.assessment_attempt.save()
        delivery_session.save()
        self._publish_session_event("assessment.delivery_session_started", delivery_session)
        return delivery_session

    def get_current_item(self, delivery_session: AssessmentDeliverySession) -> AssessmentDeliveryItem | None:
        delivery_items = self.list_delivery_items(delivery_session)
        current_item = next(
            (item for item in delivery_items if item.sequence_number == delivery_session.current_sequence_number),
            None,
        )
        if current_item:
            self.event_publisher.publish(
                BusinessEvent.create(
                    "assessment.delivery_item_presented",
                    payload={
                        "delivery_session_id": str(delivery_session.id),
                        "assessment_id": str(delivery_session.assessment_id),
                        "sequence_number": current_item.sequence_number,
                        "source_type": current_item.source_type,
                    },
                )
            )
        return current_item

    def move_to_next_item(self, delivery_session: AssessmentDeliverySession) -> AssessmentDeliveryItem | None:
        delivery_items = self.list_delivery_items(delivery_session)
        if not delivery_items:
            return None

        final_sequence_number = max(item.sequence_number for item in delivery_items)
        if delivery_session.current_sequence_number >= final_sequence_number:
            logger.info(
                "Assessment delivery session requested move beyond final item: delivery_session_id=%s current_sequence_number=%s final_sequence_number=%s",
                delivery_session.id,
                delivery_session.current_sequence_number,
                final_sequence_number,
            )
            return self.get_current_item(delivery_session)

        delivery_session.current_sequence_number += 1
        delivery_session.save()
        return self.get_current_item(delivery_session)

    def submit_response(
        self,
        delivery_session: AssessmentDeliverySession,
        item: AssessmentDeliveryItem | AssessmentItem,
        response_payload: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> AssessmentResponse:
        if delivery_session.status not in {
            AssessmentDeliveryState.CREATED,
            AssessmentDeliveryState.ACTIVE,
            AssessmentDeliveryState.SUBMITTED,
        }:
            raise LifecycleTransitionError(f"Cannot submit a delivery response while session is {delivery_session.status}.")
        attempt = self._require_attempt(delivery_session)
        assessment_item = item.item if isinstance(item, AssessmentDeliveryItem) and item.source_type == "assessment_item" else item
        if isinstance(item, AssessmentDeliveryItem) and item.source_type != "assessment_item":
            raise DomainValidationError("Assessment delivery responses can only be recorded for AssessmentItem-backed delivery items.")
        if not isinstance(assessment_item, AssessmentItem):
            raise DomainValidationError("AssessmentResponse can only be recorded for AssessmentItem-backed delivery items.")
        response = AssessmentResponse.objects.create(
            attempt=attempt,
            item=assessment_item,
            response_data=response_payload,
            metadata=metadata or {},
        )
        attempt.state = AssessmentState.SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.delivery_response_submitted",
                payload={
                    "delivery_session_id": str(delivery_session.id),
                    "assessment_id": str(delivery_session.assessment_id),
                    "attempt_id": str(delivery_session.assessment_attempt_id),
                    "item_id": str(assessment_item.id),
                    "response_id": str(response.id),
                },
            )
        )
        return response

    def submit_delivery_session(self, delivery_session: AssessmentDeliverySession) -> AssessmentDeliverySession:
        if delivery_session.status not in {
            AssessmentDeliveryState.CREATED,
            AssessmentDeliveryState.ACTIVE,
            AssessmentDeliveryState.PAUSED,
            AssessmentDeliveryState.SUBMITTED,
        }:
            raise LifecycleTransitionError(f"Cannot submit delivery session from {delivery_session.status}.")
        delivery_session.status = AssessmentDeliveryState.SUBMITTED
        delivery_session.submitted_at = timezone.now()
        if delivery_session.assessment_attempt:
            delivery_session.assessment_attempt.state = AssessmentState.SUBMITTED
            delivery_session.assessment_attempt.submitted_at = delivery_session.submitted_at
            delivery_session.assessment_attempt.save()
        delivery_session.save()
        self._publish_session_event("assessment.delivery_session_submitted", delivery_session)
        return delivery_session

    def complete_delivery_session(self, delivery_session: AssessmentDeliverySession) -> AssessmentDeliverySession:
        if delivery_session.status not in {
            AssessmentDeliveryState.CREATED,
            AssessmentDeliveryState.SUBMITTED,
            AssessmentDeliveryState.ACTIVE,
            AssessmentDeliveryState.COMPLETED,
        }:
            raise LifecycleTransitionError(f"Cannot complete delivery session from {delivery_session.status}.")
        delivery_session.status = AssessmentDeliveryState.COMPLETED
        delivery_session.completed_at = timezone.now()
        if delivery_session.assessment_attempt:
            delivery_session.assessment_attempt.state = AssessmentState.COMPLETED
            delivery_session.assessment_attempt.completed_at = delivery_session.completed_at
            delivery_session.assessment_attempt.save()
        delivery_session.save()
        self._publish_session_event("assessment.delivery_session_completed", delivery_session)
        return delivery_session

    def abandon_delivery_session(self, delivery_session: AssessmentDeliverySession) -> AssessmentDeliverySession:
        if delivery_session.status == AssessmentDeliveryState.COMPLETED:
            logger.info(
                "Ignoring abandon request for already completed delivery session: delivery_session_id=%s",
                delivery_session.id,
            )
            return delivery_session
        if delivery_session.status not in {
            AssessmentDeliveryState.CREATED,
            AssessmentDeliveryState.ACTIVE,
            AssessmentDeliveryState.PAUSED,
            AssessmentDeliveryState.SUBMITTED,
            AssessmentDeliveryState.ABANDONED,
        }:
            raise LifecycleTransitionError(f"Cannot abandon delivery session from {delivery_session.status}.")
        delivery_session.status = AssessmentDeliveryState.ABANDONED
        delivery_session.completed_at = timezone.now()
        delivery_session.save()
        self._publish_session_event("assessment.delivery_session_abandoned", delivery_session)
        return delivery_session

    def list_delivery_items(self, delivery_session: AssessmentDeliverySession) -> list[AssessmentDeliveryItem]:
        item_bank_links = list(
            AssessmentItemBankLink.objects.filter(assessment=delivery_session.assessment).order_by("sequence_number")
        )
        if item_bank_links:
            return [
                AssessmentDeliveryItem(
                    sequence_number=link.sequence_number,
                    item=link,
                    source_type="item_bank_link",
                    metadata={"item_bank_entry_id": str(link.item_bank_entry_id)},
                )
                for link in item_bank_links
            ]

        assessment_items = list(AssessmentItem.objects.filter(assessment=delivery_session.assessment).order_by("sequence_number"))
        if assessment_items:
            return [
                AssessmentDeliveryItem(
                    sequence_number=item.sequence_number,
                    item=item,
                    source_type="assessment_item",
                    metadata={"assessment_item_id": str(item.id)},
                )
                for item in assessment_items
            ]
        return []

    def list_delivery_sessions_for_learner(self, learner: User) -> list[AssessmentDeliverySession]:
        return list(AssessmentDeliverySession.objects.filter(learner=learner).order_by("-created_at"))

    def _publish_session_event(self, event_name: str, delivery_session: AssessmentDeliverySession) -> None:
        self.event_publisher.publish(
            BusinessEvent.create(
                event_name,
                payload={
                    "delivery_session_id": str(delivery_session.id),
                    "assessment_id": str(delivery_session.assessment_id),
                    "learner_id": str(delivery_session.learner_id),
                    "attempt_id": str(delivery_session.assessment_attempt_id),
                    "status": delivery_session.status,
                    "current_sequence_number": delivery_session.current_sequence_number,
                },
            )
        )

    def _require_attempt(self, delivery_session: AssessmentDeliverySession) -> AssessmentAttempt:
        if delivery_session.assessment_attempt is None:
            raise DomainValidationError("Assessment delivery session must be linked to an assessment attempt.")
        return delivery_session.assessment_attempt
