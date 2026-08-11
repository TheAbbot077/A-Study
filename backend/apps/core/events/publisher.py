import logging
from typing import Any

from django.db import transaction

from .base import BusinessEvent
from .dispatcher import EventDispatcher
from apps.core.services import RecordBusinessEventService

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, dispatcher: EventDispatcher | None = None) -> None:
        self.dispatcher = dispatcher or EventDispatcher()

    def publish(self, event: BusinessEvent) -> None:
        safe_payload = self._redact_payload(event.payload)
        record = RecordBusinessEventService().execute(event)
        logger.info(
            "Publishing business event: event_name=%s event_id=%s occurred_at=%s identifiers=%s",
            event.event_name,
            record.id,
            event.occurred_at,
            safe_payload,
        )
        transaction.on_commit(self._schedule_dispatch_pending_events)

    def _schedule_dispatch_pending_events(self) -> None:
        try:
            from apps.core.tasks import dispatch_pending_business_events_task

            dispatch_pending_business_events_task.delay()
        except Exception:  # pragma: no cover - exercised in dedicated durability tests
            logger.exception("Failed to schedule durable business-event dispatch.")

    def _redact_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {key: self._redact_value(key, value) for key, value in payload.items() if self._should_log_key(key)}

    def _should_log_key(self, key: str) -> bool:
        return key.endswith("_id") or key.endswith("_ids") or key in {
            "event_id",
            "tenant_id",
            "institution_id",
            "workspace_id",
            "learner_id",
            "actor_id",
            "status",
            "state",
            "code",
            "reason_code",
            "operation",
            "version",
            "count",
            "security_scope",
            "provider",
            "occurred_at",
        }

    def _redact_value(self, key: str, value: Any) -> Any:
        if isinstance(value, dict):
            return self._redact_payload(value)
        if isinstance(value, list):
            return [self._redact_value(key, item) for item in value]
        return value
