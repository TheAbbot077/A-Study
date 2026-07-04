from typing import Protocol, runtime_checkable

from .base import BusinessEvent


@runtime_checkable
class EventSubscriber(Protocol):
    def __call__(self, event: BusinessEvent) -> None:
        ...
