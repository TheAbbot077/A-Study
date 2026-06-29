from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.utils import timezone


@dataclass(frozen=True)
class BusinessEvent:
    event_name: str
    occurred_at: datetime
    payload: dict[str, Any]

    @classmethod
    def create(
        cls,
        event_name: str,
        payload: dict[str, Any] | None = None,
    ) -> "BusinessEvent":
        return cls(
            event_name=event_name,
            occurred_at=timezone.now(),
            payload=payload or {},
        )
