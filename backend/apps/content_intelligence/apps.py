from django.apps import AppConfig


class ContentIntelligenceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.content_intelligence"
    verbose_name = "Content Intelligence"

    def ready(self) -> None:
        from apps.content_intelligence.infrastructure.events import (
            LearningResourceUploadedSubscriber,
            StorageObjectReadySubscriber,
        )
        from apps.core.events import default_event_registry

        def subscribe_once(event_name: str, subscriber) -> None:
            existing = default_event_registry.get_subscribers(event_name)
            if any(type(item) is type(subscriber) for item in existing):
                return
            default_event_registry.subscribe(event_name, subscriber)

        subscribe_once("storage.file_uploaded", StorageObjectReadySubscriber())
        subscribe_once("academic.learning_resource_created", LearningResourceUploadedSubscriber())
