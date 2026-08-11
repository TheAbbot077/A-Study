from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from .base_models import TimestampedModel, UUIDModel


class BusinessEventDeliveryStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    FAILED_RETRYABLE = "FAILED_RETRYABLE", "Failed retryable"
    DELIVERED = "DELIVERED", "Delivered"
    FAILED_TERMINAL = "FAILED_TERMINAL", "Failed terminal"


class BusinessEventRecord(UUIDModel, TimestampedModel):
    event_type = models.CharField(max_length=160)
    source_entity_type = models.CharField(max_length=160, blank=True, default="")
    source_entity_id = models.CharField(max_length=160, blank=True, default="")
    tenant = models.ForeignKey(
        "users.Institution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_events",
    )
    safe_payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField()
    correlation_id = models.UUIDField(null=True, blank=True)
    causation_event_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "core_business_event"
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["event_type", "occurred_at"], name="core_bus_evt_type_occur_idx"),
            models.Index(fields=["source_entity_type", "source_entity_id"], name="core_bus_evt_source_idx"),
            models.Index(fields=["tenant", "occurred_at"], name="core_bus_evt_tenant_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"BusinessEventRecord {self.id} ({self.event_type})"


class BusinessEventDelivery(UUIDModel, TimestampedModel):
    event = models.ForeignKey(BusinessEventRecord, on_delete=models.CASCADE, related_name="deliveries")
    consumer_key = models.CharField(max_length=200)
    status = models.CharField(
        max_length=24,
        choices=BusinessEventDeliveryStatus.choices,
        default=BusinessEventDeliveryStatus.PENDING,
    )
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=96, blank=True, default="")
    failure_detail_safe = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "core_business_event_delivery"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "consumer_key"], name="uniq_evt_consumer_delivery")
        ]
        indexes = [
            models.Index(fields=["status", "next_attempt_at"], name="core_bus_evt_deliv_retry_idx"),
            models.Index(fields=["status", "processing_started_at"], name="core_bus_evt_deliv_proc_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"BusinessEventDelivery {self.id} ({self.consumer_key})"
