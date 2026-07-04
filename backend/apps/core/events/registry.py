from .subscribers import EventSubscriber


class EventRegistry:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventSubscriber]] = {}

    def subscribe(self, event_name: str, subscriber: EventSubscriber) -> None:
        self._subscribers.setdefault(event_name, []).append(subscriber)

    def get_subscribers(self, event_name: str) -> list[EventSubscriber]:
        return list(self._subscribers.get(event_name, []))

    def clear(self) -> None:
        self._subscribers.clear()


default_event_registry = EventRegistry()

# Settings platform event names
for event_name in [
    "settings.user_setting_changed",
    "settings.user_setting_deleted",
    "settings.institution_setting_changed",
    "settings.institution_setting_deleted",
    "audit.entry_recorded",
]:
    default_event_registry._subscribers.setdefault(event_name, [])
