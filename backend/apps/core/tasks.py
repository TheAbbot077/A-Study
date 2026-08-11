from __future__ import annotations

from celery import shared_task

from apps.core.services import DispatchBusinessEventDeliveryService, DispatchPendingBusinessEventsService


@shared_task(name="core.dispatch_business_event_delivery")
def dispatch_business_event_delivery_task(delivery_id: str) -> None:
    DispatchBusinessEventDeliveryService().execute(delivery_id)


@shared_task(name="core.dispatch_pending_business_events")
def dispatch_pending_business_events_task(batch_size: int = 100) -> None:
    delivery_ids = DispatchPendingBusinessEventsService(batch_size=batch_size).execute()
    for delivery_id in delivery_ids:
        dispatch_business_event_delivery_task.delay(delivery_id)
