import logging
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from apps.notifications.domain.models import Notification

logger = logging.getLogger(__name__)


@runtime_checkable
class NotificationChannelProvider(Protocol):
    def send(self, notification: Notification) -> None:
        ...


class LoggingNotificationChannelProvider:
    def send(self, notification: Notification) -> None:
        logger.info(
            "Notification queued for delivery: channel=%s recipient=%s subject=%s",
            notification.channel,
            notification.recipient_email,
            notification.subject,
        )
