from __future__ import annotations

from typing import Any, Optional

from apps.audit.domain.models import AuditEntry
from apps.core.events import BusinessEvent, EventPublisher


class AuditService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def record_action(
        self,
        actor=None,
        institution=None,
        action: str = "",
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        target_display: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEntry:
        entry = AuditEntry.objects.create(
            actor=actor,
            institution=institution,
            action=action,
            target_type=target_type or "",
            target_id=target_id or "",
            target_display=target_display or "",
            metadata=metadata or {},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "audit.entry_recorded",
                payload={
                    "audit_id": str(entry.id),
                    "action": entry.action,
                    "target_type": entry.target_type,
                    "target_id": entry.target_id,
                },
            )
        )
        return entry

    def list_for_actor(self, actor) -> list[AuditEntry]:
        return list(AuditEntry.objects.filter(actor=actor).order_by("-created_at"))

    def list_for_institution(self, institution) -> list[AuditEntry]:
        return list(AuditEntry.objects.filter(institution=institution).order_by("-created_at"))

    def list_for_target(self, target_type: str, target_id: str) -> list[AuditEntry]:
        return list(
            AuditEntry.objects.filter(target_type=target_type, target_id=target_id).order_by("-created_at")
        )
