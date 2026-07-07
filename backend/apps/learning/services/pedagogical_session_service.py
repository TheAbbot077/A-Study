from __future__ import annotations

from typing import Any, Optional

from django.db.models import Max
from django.utils import timezone

from apps.academic.domain.models import ContentConcept
from apps.core.events import BusinessEvent, EventPublisher
from apps.learning.domain.models import PedagogicalMessage, PedagogicalSession, PedagogicalState
from apps.users.domain.models import User


class PedagogicalSessionService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def create_session(self, learner: User, content_concept: ContentConcept) -> PedagogicalSession:
        session = PedagogicalSession.objects.create(
            learner=learner,
            content_concept=content_concept,
            status=PedagogicalState.CREATED,
        )
        self._publish_session_event("pedagogy.session_created", session)
        return session

    def start_session(self, session: PedagogicalSession) -> PedagogicalSession:
        return self._transition_session(
            session,
            target_status=PedagogicalState.ACTIVE,
            event_name="pedagogy.session_started",
            allowed_statuses={PedagogicalState.CREATED},
        )

    def pause_session(self, session: PedagogicalSession) -> PedagogicalSession:
        return self._transition_session(
            session,
            target_status=PedagogicalState.PAUSED,
            event_name="pedagogy.session_paused",
            allowed_statuses={PedagogicalState.ACTIVE},
        )

    def resume_session(self, session: PedagogicalSession) -> PedagogicalSession:
        return self._transition_session(
            session,
            target_status=PedagogicalState.ACTIVE,
            event_name="pedagogy.session_resumed",
            allowed_statuses={PedagogicalState.PAUSED},
        )

    def complete_session(self, session: PedagogicalSession) -> PedagogicalSession:
        return self._transition_session(
            session,
            target_status=PedagogicalState.COMPLETED,
            event_name="pedagogy.session_completed",
            allowed_statuses={PedagogicalState.ACTIVE, PedagogicalState.PAUSED},
            ends_session=True,
        )

    def abandon_session(self, session: PedagogicalSession) -> PedagogicalSession:
        return self._transition_session(
            session,
            target_status=PedagogicalState.ABANDONED,
            event_name="pedagogy.session_abandoned",
            allowed_statuses={PedagogicalState.CREATED, PedagogicalState.ACTIVE, PedagogicalState.PAUSED},
            ends_session=True,
        )

    def add_message(
        self,
        session: PedagogicalSession,
        sender_type: str,
        message_type: str,
        content: str,
        sequence_number: int | None = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> PedagogicalMessage:
        if sequence_number is None:
            sequence_number = self._next_sequence_number(session)
        if sequence_number < 1:
            raise ValueError("Pedagogical message sequence_number must be greater than or equal to 1.")

        message = PedagogicalMessage.objects.create(
            pedagogical_session=session,
            sender_type=sender_type,
            message_type=message_type,
            content=content,
            sequence_number=sequence_number,
            metadata=metadata or {},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "pedagogy.message_added",
                payload={
                    "message_id": str(message.id),
                    "session_id": str(session.id),
                    "sender_type": message.sender_type,
                    "message_type": message.message_type,
                    "sequence_number": message.sequence_number,
                },
            )
        )
        return message

    def list_messages(self, session: PedagogicalSession) -> list[PedagogicalMessage]:
        return list(PedagogicalMessage.objects.filter(pedagogical_session=session).order_by("sequence_number"))

    def _transition_session(
        self,
        session: PedagogicalSession,
        target_status: str,
        event_name: str,
        allowed_statuses: set[str],
        ends_session: bool = False,
    ) -> PedagogicalSession:
        if session.status not in allowed_statuses:
            raise ValueError(f"Cannot transition pedagogical session from {session.status} to {target_status}.")

        session.status = target_status
        if ends_session:
            session.ended_at = timezone.now()
        session.save()
        self._publish_session_event(event_name, session)
        return session

    def _next_sequence_number(self, session: PedagogicalSession) -> int:
        highest_sequence = (
            PedagogicalMessage.objects.filter(pedagogical_session=session).aggregate(highest=Max("sequence_number"))["highest"]
            or 0
        )
        return highest_sequence + 1

    def _publish_session_event(self, event_name: str, session: PedagogicalSession) -> None:
        self.event_publisher.publish(
            BusinessEvent.create(
                event_name,
                payload={
                    "session_id": str(session.id),
                    "learner_id": str(session.learner_id),
                    "content_concept_id": str(session.content_concept_id),
                    "status": session.status,
                },
            )
        )
