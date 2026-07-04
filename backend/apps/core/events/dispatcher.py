import logging

from .registry import EventRegistry
from .base import BusinessEvent

logger = logging.getLogger(__name__)


class EventDispatcher:
    def __init__(self, registry: EventRegistry | None = None) -> None:
        self.registry = registry or EventRegistry()

    def dispatch(self, event: BusinessEvent) -> None:
        for subscriber in self.registry.get_subscribers(event.event_name):
            try:
                subscriber(event)
            except Exception:
                logger.exception(
                    "Subscriber failed for event_name=%s",
                    event.event_name,
                )
