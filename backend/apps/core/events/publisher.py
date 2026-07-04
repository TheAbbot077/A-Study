import logging

from .base import BusinessEvent
from .dispatcher import EventDispatcher

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, dispatcher: EventDispatcher | None = None) -> None:
        self.dispatcher = dispatcher or EventDispatcher()

    def publish(self, event: BusinessEvent) -> None:
        logger.info(
            "Publishing business event: event_name=%s occurred_at=%s payload=%s",
            event.event_name,
            event.occurred_at,
            event.payload,
        )
        self.dispatcher.dispatch(event)
