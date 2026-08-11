from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.utils import timezone


@dataclass(frozen=True)
class BusinessEvent:
    event_name: str
    occurred_at: datetime
    payload: dict[str, Any]
    source_entity_type: str = ""
    source_entity_id: str = ""
    tenant_id: str | None = None
    correlation_id: str | None = None
    causation_event_id: str | None = None

    @classmethod
    def create(
        cls,
        event_name: str,
        payload: dict[str, Any] | None = None,
        *,
        source_entity_type: str = "",
        source_entity_id: str = "",
        tenant_id: str | None = None,
        correlation_id: str | None = None,
        causation_event_id: str | None = None,
    ) -> "BusinessEvent":
        return cls(
            event_name=event_name,
            occurred_at=timezone.now(),
            payload=payload or {},
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            causation_event_id=causation_event_id,
        )
