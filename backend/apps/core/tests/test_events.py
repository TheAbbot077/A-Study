from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from apps.core.events import (
    BusinessEvent,
    EventDispatcher,
    EventPublisher,
    EventRegistry,
)
from apps.users.services.identity_service import IdentityService


def test_business_event_create_creates_event_with_payload():
    event = BusinessEvent.create("identity.user_registered", payload={"user_id": "1"})

    assert event.event_name == "identity.user_registered"
    assert event.payload == {"user_id": "1"}
    assert isinstance(event.occurred_at, datetime)


def test_event_registry_can_subscribe_and_retrieve_subscribers():
    registry = EventRegistry()
    subscriber = Mock()

    registry.subscribe("identity.user_registered", subscriber)

    assert registry.get_subscribers("identity.user_registered") == [subscriber]
    assert registry.get_subscribers("identity.user_logged_in") == []


def test_event_dispatcher_calls_subscribers():
    registry = EventRegistry()
    subscriber = Mock()
    registry.subscribe("identity.user_registered", subscriber)
    dispatcher = EventDispatcher(registry)
    event = BusinessEvent.create("identity.user_registered")

    dispatcher.dispatch(event)

    subscriber.assert_called_once_with(event)


def test_event_dispatcher_continues_when_one_subscriber_fails():
    registry = EventRegistry()
    failing_subscriber = Mock(side_effect=RuntimeError("boom"))
    succeeding_subscriber = Mock()
    registry.subscribe("identity.user_registered", failing_subscriber)
    registry.subscribe("identity.user_registered", succeeding_subscriber)
    dispatcher = EventDispatcher(registry)
    event = BusinessEvent.create("identity.user_registered")

    with patch("apps.core.events.dispatcher.logger") as logger:
        dispatcher.dispatch(event)

    failing_subscriber.assert_called_once_with(event)
    succeeding_subscriber.assert_called_once_with(event)
    logger.exception.assert_called_once()


def test_event_publisher_dispatches_events():
    dispatcher = Mock()
    publisher = EventPublisher(dispatcher=dispatcher)
    event = BusinessEvent.create("identity.user_registered")

    publisher.publish(event)

    dispatcher.dispatch.assert_called_once_with(event)


def test_identity_service_register_user_publishes_identity_event():
    publisher = Mock()
    service = IdentityService(event_publisher=publisher)
    user = SimpleNamespace(id="user-123", email="user@example.com")

    with patch("apps.users.services.identity_service.User.objects") as user_objects, patch(
        "apps.users.services.identity_service.Profile.objects"
    ) as profile_objects:
        user_objects.create_user.return_value = user
        profile_objects.create.return_value = None

        created_user = service.register_user("user@example.com", "secret", "Demo")

    assert created_user is user
    publisher.publish.assert_called_once()
    published_event = publisher.publish.call_args.args[0]
    assert published_event.event_name == "identity.user_registered"
    assert published_event.payload == {"user_id": "user-123", "email": "user@example.com"}
