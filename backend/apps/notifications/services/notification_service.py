from __future__ import annotations

import logging
from typing import Any, Optional

from apps.core.events import BusinessEvent, EventPublisher
from apps.notifications.domain.models import Notification, NotificationChannel, NotificationStatus
from apps.notifications.infrastructure.channels import NotificationChannelProvider

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
        self,
        channel_provider: Optional[NotificationChannelProvider] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.channel_provider = channel_provider or LoggingNotificationChannelProvider()
        self.event_publisher = event_publisher or EventPublisher()

    def create_notification(
        self,
        *,
        recipient_email: str = "",
        channel: str = NotificationChannel.EMAIL,
        subject: str = "",
        body: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> Notification:
        notification = Notification.objects.create(
            recipient_email=recipient_email,
            channel=channel,
            subject=subject,
            body=body,
            status=NotificationStatus.PENDING,
            metadata=metadata or {},
        )

        self.event_publisher.publish(
            BusinessEvent.create(
                "notifications.notification_created",
                payload={
                    "notification_id": str(notification.id),
                    "channel": notification.channel,
                    "recipient_email": notification.recipient_email,
                },
            )
        )
        return notification

    def send_notification(self, notification: Notification) -> Notification:
        try:
            self.channel_provider.send(notification)
        except Exception:
            notification.status = NotificationStatus.FAILED
            notification.save(update_fields=["status", "updated_at"])
            logger.exception("Notification delivery failed")
            raise

        notification.status = NotificationStatus.SENT
        notification.save(update_fields=["status", "updated_at"])

        self.event_publisher.publish(
            BusinessEvent.create(
                "notifications.notification_sent",
                payload={
                    "notification_id": str(notification.id),
                    "channel": notification.channel,
                    "recipient_email": notification.recipient_email,
                },
            )
        )
        return notification

    def create_and_send(
        self,
        *,
        recipient_email: str = "",
        channel: str = NotificationChannel.EMAIL,
        subject: str = "",
        body: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> Notification:
        notification = self.create_notification(
            recipient_email=recipient_email,
            channel=channel,
            subject=subject,
            body=body,
            metadata=metadata,
        )
        return self.send_notification(notification)
