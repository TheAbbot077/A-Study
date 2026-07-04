from unittest.mock import Mock, patch

from apps.notifications.domain.models import Notification, NotificationChannel, NotificationStatus
from apps.notifications.services.notification_service import NotificationService


def test_notification_creation_publishes_created_event():
    publisher = Mock()
    service = NotificationService(channel_provider=Mock(), event_publisher=publisher)

    with patch("apps.notifications.services.notification_service.Notification.objects") as objs:
        fake_notification = Mock(spec=Notification)
        fake_notification.id = "notification-1"
        fake_notification.channel = NotificationChannel.EMAIL
        fake_notification.recipient_email = "user@example.com"
        objs.create.return_value = fake_notification

        notification = service.create_notification(
            recipient_email="user@example.com",
            channel=NotificationChannel.EMAIL,
            subject="Welcome",
            body="Hello",
        )

    assert notification is fake_notification
    publisher.publish.assert_called_once()
    event = publisher.publish.call_args.args[0]
    assert event.event_name == "notifications.notification_created"


def test_notification_send_marks_sent_and_publishes_sent_event():
    provider = Mock()
    publisher = Mock()
    service = NotificationService(channel_provider=provider, event_publisher=publisher)

    notification = Notification(
        recipient_email="user@example.com",
        channel=NotificationChannel.EMAIL,
        subject="Welcome",
        body="Hello",
        status=NotificationStatus.PENDING,
    )

    with patch.object(Notification, "save") as save_mock:
        service.send_notification(notification)

    provider.send.assert_called_once_with(notification)
    assert notification.status == NotificationStatus.SENT
    publisher.publish.assert_called_once()
    event = publisher.publish.call_args.args[0]
    assert event.event_name == "notifications.notification_sent"


def test_failed_send_marks_failed():
    provider = Mock()
    provider.send.side_effect = RuntimeError("boom")
    publisher = Mock()
    service = NotificationService(channel_provider=provider, event_publisher=publisher)

    notification = Notification(
        recipient_email="user@example.com",
        channel=NotificationChannel.EMAIL,
        subject="Welcome",
        body="Hello",
        status=NotificationStatus.PENDING,
    )

    with patch.object(Notification, "save") as save_mock:
        try:
            service.send_notification(notification)
        except RuntimeError:
            pass

    assert notification.status == NotificationStatus.FAILED
