from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from apps.core.events import BusinessEvent, EventPublisher
from apps.core.events.registry import EventRegistry
from apps.core.models import BusinessEventDelivery, BusinessEventDeliveryStatus, BusinessEventRecord
from apps.core.services import (
    DispatchBusinessEventDeliveryService,
    DispatchPendingBusinessEventsService,
    RecordBusinessEventService,
)


@pytest.mark.django_db
def test_record_business_event_creates_durable_event_and_delivery():
    registry = EventRegistry()
    registry.subscribe("identity.user_registered", lambda event: None, consumer_key="identity.user_registered.audit")

    event = BusinessEvent.create("identity.user_registered", payload={"user_id": "user-1", "display_name": "Demo"})
    with patch("apps.core.services.durable_events.default_event_registry", registry):
        record = RecordBusinessEventService().execute(event)

    assert BusinessEventRecord.objects.filter(id=record.id).exists()
    delivery = BusinessEventDelivery.objects.get(event=record)
    assert delivery.consumer_key == "identity.user_registered.audit"
    assert delivery.status == BusinessEventDeliveryStatus.PENDING
    assert record.safe_payload == {"user_id": "user-1"}


@pytest.mark.django_db
def test_record_business_event_rolls_back_with_outer_transaction():
    registry = EventRegistry()
    registry.subscribe("identity.user_registered", lambda event: None, consumer_key="identity.user_registered.rollback")

    with pytest.raises(RuntimeError):
        from django.db import transaction

        with patch("apps.core.services.durable_events.default_event_registry", registry):
            with transaction.atomic():
                RecordBusinessEventService().execute(BusinessEvent.create("identity.user_registered", payload={"user_id": "user-1"}))
                raise RuntimeError("boom")

    assert BusinessEventRecord.objects.count() == 0
    assert BusinessEventDelivery.objects.count() == 0


@pytest.mark.django_db
def test_pending_sweep_claims_due_deliveries():
    registry = EventRegistry()
    registry.subscribe("identity.user_registered", lambda event: None, consumer_key="identity.user_registered.sweep")
    with patch("apps.core.services.durable_events.default_event_registry", registry):
        record = RecordBusinessEventService().execute(BusinessEvent.create("identity.user_registered", payload={"user_id": "user-1"}))
        claimed_ids = DispatchPendingBusinessEventsService(batch_size=10).execute()

    assert claimed_ids == [str(BusinessEventDelivery.objects.get(event=record).id)]
    delivery = BusinessEventDelivery.objects.get(event=record)
    assert delivery.status == BusinessEventDeliveryStatus.PENDING
    assert delivery.attempt_count == 0


@pytest.mark.django_db
def test_delivery_dispatch_marks_delivered_and_invokes_consumer():
    consumer = Mock()
    registry = EventRegistry()
    registry.subscribe("identity.user_registered", consumer, consumer_key="identity.user_registered.delivery")
    with patch("apps.core.services.durable_events.default_event_registry", registry):
        record = RecordBusinessEventService().execute(BusinessEvent.create("identity.user_registered", payload={"user_id": "user-1"}))
        delivery = BusinessEventDelivery.objects.get(event=record)

        outcome = DispatchBusinessEventDeliveryService(registry=registry).execute(str(delivery.id))

    delivery.refresh_from_db()
    assert outcome.status == BusinessEventDeliveryStatus.DELIVERED
    assert delivery.status == BusinessEventDeliveryStatus.DELIVERED
    consumer.assert_called_once()


@pytest.mark.django_db
def test_scheduling_failure_leaves_event_pending():
    registry = EventRegistry()
    registry.subscribe("identity.user_registered", lambda event: None, consumer_key="identity.user_registered.pending")

    with patch("apps.core.services.durable_events.default_event_registry", registry), patch(
        "apps.core.tasks.dispatch_pending_business_events_task.delay",
        side_effect=RuntimeError("broker unavailable"),
    ):
        EventPublisher(dispatcher=Mock()).publish(BusinessEvent.create("identity.user_registered", payload={"user_id": "user-1"}))

    record = BusinessEventRecord.objects.get(event_type="identity.user_registered")
    delivery = BusinessEventDelivery.objects.get(event=record)
    assert delivery.status == BusinessEventDeliveryStatus.PENDING
