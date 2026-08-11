from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.events.base import BusinessEvent
from apps.core.events.dispatcher import EventDispatcher
from apps.core.events.registry import EventRegistry, default_event_registry
from apps.core.models import BusinessEventDelivery, BusinessEventDeliveryStatus, BusinessEventRecord


SAFE_PAYLOAD_KEYS = {
    "event_id",
    "tenant_id",
    "institution_id",
    "workspace_id",
    "learner_id",
    "actor_id",
    "assessment_id",
    "attempt_id",
    "delivery_id",
    "session_id",
    "job_id",
    "run_id",
    "manifest_id",
    "resource_id",
    "file_id",
    "response_id",
    "response_ids",
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


@dataclass(frozen=True)
class DispatchOutcome:
    delivery_id: str
    status: str
    failure_code: str = ""
    failure_detail_safe: str = ""


class RecordBusinessEventService:
    def __init__(self, *, registry: EventRegistry | None = None) -> None:
        self.registry = registry or default_event_registry

    @transaction.atomic
    def execute(self, event: BusinessEvent) -> BusinessEventRecord:
        record = BusinessEventRecord.objects.create(
            event_type=event.event_name,
            source_entity_type=event.source_entity_type or self._default_source_type(event.event_name),
            source_entity_id=event.source_entity_id or self._extract_source_entity_id(event.payload),
            tenant_id=event.tenant_id or None,
            safe_payload=self._sanitize_payload(event.payload),
            occurred_at=event.occurred_at,
            correlation_id=event.correlation_id or None,
            causation_event_id=event.causation_event_id or None,
        )
        deliveries = [
            BusinessEventDelivery(event=record, consumer_key=registration.consumer_key)
            for registration in self.registry.get_registrations(event.event_name)
        ]
        if deliveries:
            BusinessEventDelivery.objects.bulk_create(deliveries)
        return record

    def _default_source_type(self, event_name: str) -> str:
        return event_name.split(".", 1)[0] if "." in event_name else event_name

    def _extract_source_entity_id(self, payload: dict[str, Any]) -> str:
        for key, value in payload.items():
            if key.endswith("_id") and value is not None and value != "":
                return str(value)
        return ""

    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in payload.items():
            if key in SAFE_PAYLOAD_KEYS or key.endswith("_id") or key.endswith("_ids"):
                sanitized[key] = self._sanitize_value(value)
        return sanitized

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._sanitize_value(item) for key, item in value.items() if key in SAFE_PAYLOAD_KEYS or key.endswith("_id") or key.endswith("_ids")}
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        return value


class DispatchBusinessEventDeliveryService:
    max_retries = 5
    retry_delay = timedelta(minutes=5)
    stale_processing_lease = timedelta(minutes=15)

    def __init__(
        self,
        *,
        registry: EventRegistry | None = None,
        dispatcher: EventDispatcher | None = None,
    ) -> None:
        self.registry = registry or default_event_registry
        self.dispatcher = dispatcher or EventDispatcher(self.registry)

    def execute(self, delivery_id: str) -> DispatchOutcome:
        with transaction.atomic():
            delivery = (
                BusinessEventDelivery.objects.select_for_update()
                .select_related("event")
                .filter(id=delivery_id)
                .first()
            )
            if delivery is None:
                return DispatchOutcome(delivery_id=delivery_id, status=BusinessEventDeliveryStatus.FAILED_TERMINAL, failure_code="EVENT_CONSUMER_NOT_FOUND")
            if delivery.status == BusinessEventDeliveryStatus.DELIVERED:
                return DispatchOutcome(delivery_id=str(delivery.id), status=delivery.status)
            if delivery.status == BusinessEventDeliveryStatus.FAILED_TERMINAL:
                return DispatchOutcome(delivery_id=str(delivery.id), status=delivery.status, failure_code=delivery.failure_code, failure_detail_safe=delivery.failure_detail_safe)
            if delivery.status == BusinessEventDeliveryStatus.PROCESSING and delivery.processing_started_at:
                if delivery.processing_started_at >= timezone.now() - self.stale_processing_lease:
                    return DispatchOutcome(delivery_id=str(delivery.id), status=delivery.status)
            delivery.status = BusinessEventDeliveryStatus.PROCESSING
            delivery.processing_started_at = timezone.now()
            delivery.last_attempt_at = timezone.now()
            delivery.attempt_count += 1
            delivery.failure_code = ""
            delivery.failure_detail_safe = ""
            delivery.save(update_fields=["status", "processing_started_at", "last_attempt_at", "attempt_count", "failure_code", "failure_detail_safe", "updated_at"])

        return self._dispatch_claimed_delivery(delivery_id)

    def _dispatch_claimed_delivery(self, delivery_id: str) -> DispatchOutcome:
        delivery = BusinessEventDelivery.objects.select_related("event").filter(id=delivery_id).first()
        if delivery is None:
            return DispatchOutcome(delivery_id=delivery_id, status=BusinessEventDeliveryStatus.FAILED_TERMINAL, failure_code="EVENT_CONSUMER_NOT_FOUND")
        registration = self.registry.get_registration(delivery.event.event_type, delivery.consumer_key)
        if registration is None:
            return self._finalize_terminal(delivery, "EVENT_CONSUMER_NOT_FOUND", "Registered consumer could not be resolved.")

        event = BusinessEvent.create(
            delivery.event.event_type,
            payload=delivery.event.safe_payload,
            source_entity_type=delivery.event.source_entity_type,
            source_entity_id=delivery.event.source_entity_id,
            tenant_id=str(delivery.event.tenant_id) if delivery.event.tenant_id else None,
            correlation_id=str(delivery.event.correlation_id) if delivery.event.correlation_id else None,
            causation_event_id=str(delivery.event.causation_event_id) if delivery.event.causation_event_id else None,
        )

        try:
            registration.subscriber(event)
        except Exception as exc:  # pragma: no cover - exercised in dedicated tests
            if delivery.attempt_count >= self.max_retries:
                return self._finalize_terminal(delivery, "EVENT_DELIVERY_TERMINAL", self._safe_exception(exc))
            return self._finalize_retryable(delivery, "EVENT_DELIVERY_RETRYABLE", self._safe_exception(exc))

        return self._finalize_delivered(delivery)

    @transaction.atomic
    def _finalize_delivered(self, delivery: BusinessEventDelivery) -> DispatchOutcome:
        delivery = BusinessEventDelivery.objects.select_for_update().get(id=delivery.id)
        delivery.status = BusinessEventDeliveryStatus.DELIVERED
        delivery.delivered_at = timezone.now()
        delivery.processing_started_at = None
        delivery.next_attempt_at = None
        delivery.failure_code = ""
        delivery.failure_detail_safe = ""
        delivery.save(update_fields=["status", "delivered_at", "processing_started_at", "next_attempt_at", "failure_code", "failure_detail_safe", "updated_at"])
        return DispatchOutcome(delivery_id=str(delivery.id), status=delivery.status)

    @transaction.atomic
    def _finalize_retryable(self, delivery: BusinessEventDelivery, code: str, detail: str) -> DispatchOutcome:
        delivery = BusinessEventDelivery.objects.select_for_update().get(id=delivery.id)
        delivery.status = BusinessEventDeliveryStatus.FAILED_RETRYABLE
        delivery.next_attempt_at = timezone.now() + self.retry_delay
        delivery.processing_started_at = None
        delivery.failure_code = code
        delivery.failure_detail_safe = detail[:500]
        delivery.save(update_fields=["status", "next_attempt_at", "processing_started_at", "failure_code", "failure_detail_safe", "updated_at"])
        return DispatchOutcome(delivery_id=str(delivery.id), status=delivery.status, failure_code=delivery.failure_code, failure_detail_safe=delivery.failure_detail_safe)

    @transaction.atomic
    def _finalize_terminal(self, delivery: BusinessEventDelivery, code: str, detail: str) -> DispatchOutcome:
        delivery = BusinessEventDelivery.objects.select_for_update().get(id=delivery.id)
        delivery.status = BusinessEventDeliveryStatus.FAILED_TERMINAL
        delivery.next_attempt_at = None
        delivery.processing_started_at = None
        delivery.failure_code = code
        delivery.failure_detail_safe = detail[:500]
        delivery.save(update_fields=["status", "next_attempt_at", "processing_started_at", "failure_code", "failure_detail_safe", "updated_at"])
        return DispatchOutcome(delivery_id=str(delivery.id), status=delivery.status, failure_code=delivery.failure_code, failure_detail_safe=delivery.failure_detail_safe)

    def _safe_exception(self, exc: Exception) -> str:
        return f"{exc.__class__.__name__}"


class DispatchPendingBusinessEventsService:
    def __init__(self, *, batch_size: int = 100) -> None:
        self.batch_size = batch_size

    @transaction.atomic
    def execute(self) -> list[str]:
        now = timezone.now()
        due_delivery_ids = list(
            BusinessEventDelivery.objects.select_for_update(skip_locked=True)
            .filter(
                Q(status=BusinessEventDeliveryStatus.PENDING)
                | Q(status=BusinessEventDeliveryStatus.FAILED_RETRYABLE, next_attempt_at__lte=now)
                | Q(status=BusinessEventDeliveryStatus.PROCESSING, processing_started_at__lt=now - DispatchBusinessEventDeliveryService.stale_processing_lease)
            )
            .order_by("created_at")
            .values_list("id", flat=True)[: self.batch_size]
        )
        return [str(delivery_id) for delivery_id in due_delivery_ids]


class ReconcileBusinessEventDeliveryService:
    def __init__(self, *, batch_size: int = 100) -> None:
        self.batch_size = batch_size

    @transaction.atomic
    def execute(self) -> list[str]:
        cutoff = timezone.now() - DispatchBusinessEventDeliveryService.stale_processing_lease
        reclaimed = list(
            BusinessEventDelivery.objects.select_for_update(skip_locked=True)
            .filter(status=BusinessEventDeliveryStatus.PROCESSING, processing_started_at__lt=cutoff)
            .order_by("created_at")[: self.batch_size]
        )
        ids: list[str] = []
        for delivery in reclaimed:
            delivery.status = BusinessEventDeliveryStatus.FAILED_RETRYABLE
            delivery.next_attempt_at = timezone.now()
            delivery.processing_started_at = None
            delivery.failure_code = "EVENT_PROCESSING_LEASE_EXPIRED"
            delivery.failure_detail_safe = "Processing lease expired before completion."
            delivery.save(update_fields=["status", "next_attempt_at", "processing_started_at", "failure_code", "failure_detail_safe", "updated_at"])
            ids.append(str(delivery.id))
        return ids
