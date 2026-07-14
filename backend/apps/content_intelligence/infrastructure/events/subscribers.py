from __future__ import annotations

from apps.core.events import BusinessEvent


class StorageObjectReadySubscriber:
    def __call__(self, event: BusinessEvent) -> None:
        return None


class LearningResourceUploadedSubscriber:
    def __call__(self, event: BusinessEvent) -> None:
        return None
