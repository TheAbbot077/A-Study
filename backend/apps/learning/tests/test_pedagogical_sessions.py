from unittest.mock import Mock, patch

from django.db import models
from django.test import SimpleTestCase

from apps.core.events import default_event_registry
from apps.learning.domain.models import PedagogicalMessage, PedagogicalSession, PedagogicalState
from apps.learning.services import PedagogicalSessionService


class DummyLearner:
    id = "learner-1"


class DummyContentConcept:
    id = "concept-1"


class DummySession:
    id = "session-1"
    learner_id = "learner-1"
    content_concept_id = "concept-1"

    def __init__(self, status=PedagogicalState.CREATED):
        self.status = status
        self.ended_at = None
        self.save = Mock()


class PedagogicalSessionModelTests(SimpleTestCase):
    def test_supported_session_statuses(self):
        self.assertEqual(
            {choice[0] for choice in PedagogicalState.choices},
            {"created", "active", "paused", "completed", "abandoned"},
        )

    def test_supported_sender_and_message_types(self):
        self.assertEqual(
            {choice[0] for choice in PedagogicalMessage.SenderType.choices},
            {"learner", "abbot", "ariel", "system"},
        )
        self.assertEqual(
            {choice[0] for choice in PedagogicalMessage.MessageType.choices},
            {"explanation", "question", "response", "clarification", "summary", "system"},
        )

    def test_message_sequence_constraints_and_ordering_are_declared(self):
        self.assertEqual(PedagogicalMessage._meta.ordering, ["sequence_number"])

        constraints = {constraint.name: constraint for constraint in PedagogicalMessage._meta.constraints}

        unique_constraint = constraints["unique_pedagogical_session_sequence"]
        self.assertIsInstance(unique_constraint, models.UniqueConstraint)
        self.assertEqual(tuple(unique_constraint.fields), ("pedagogical_session", "sequence_number"))

        check_constraint = constraints["pedagogical_message_sequence_gte_1"]
        self.assertIsInstance(check_constraint, models.CheckConstraint)
        self.assertIn("sequence_number__gte", str(check_constraint.condition))


class PedagogicalSessionServiceTests(SimpleTestCase):
    def test_create_session_publishes_event(self):
        publisher = Mock()
        service = PedagogicalSessionService(event_publisher=publisher)
        learner = DummyLearner()
        content_concept = DummyContentConcept()

        with patch("apps.learning.services.pedagogical_session_service.PedagogicalSession.objects") as session_objects:
            fake_session = DummySession()
            session_objects.create.return_value = fake_session

            session = service.create_session(learner, content_concept)

        self.assertIs(session, fake_session)
        session_objects.create.assert_called_once_with(
            learner=learner,
            content_concept=content_concept,
            status=PedagogicalState.CREATED,
        )
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "pedagogy.session_created")
        self.assertEqual(event.payload["session_id"], "session-1")

    def test_session_lifecycle_transitions_publish_events(self):
        publisher = Mock()
        service = PedagogicalSessionService(event_publisher=publisher)
        session = DummySession()

        service.start_session(session)
        self.assertEqual(session.status, PedagogicalState.ACTIVE)

        service.pause_session(session)
        self.assertEqual(session.status, PedagogicalState.PAUSED)

        service.resume_session(session)
        self.assertEqual(session.status, PedagogicalState.ACTIVE)

        service.complete_session(session)
        self.assertEqual(session.status, PedagogicalState.COMPLETED)
        self.assertIsNotNone(session.ended_at)

        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            [
                "pedagogy.session_started",
                "pedagogy.session_paused",
                "pedagogy.session_resumed",
                "pedagogy.session_completed",
            ],
        )
        self.assertEqual(session.save.call_count, 4)

    def test_abandon_session_publishes_event_and_sets_ended_at(self):
        publisher = Mock()
        service = PedagogicalSessionService(event_publisher=publisher)
        session = DummySession(status=PedagogicalState.ACTIVE)

        service.abandon_session(session)

        self.assertEqual(session.status, PedagogicalState.ABANDONED)
        self.assertIsNotNone(session.ended_at)
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "pedagogy.session_abandoned")

    def test_invalid_lifecycle_transition_raises(self):
        service = PedagogicalSessionService(event_publisher=Mock())
        session = DummySession(status=PedagogicalState.COMPLETED)

        with self.assertRaises(ValueError):
            service.pause_session(session)

    def test_add_message_creates_message_and_publishes_event(self):
        publisher = Mock()
        service = PedagogicalSessionService(event_publisher=publisher)
        session = DummySession(status=PedagogicalState.ACTIVE)

        with patch("apps.learning.services.pedagogical_session_service.PedagogicalMessage.objects") as message_objects:
            fake_message = Mock(spec=PedagogicalMessage)
            fake_message.id = "message-1"
            fake_message.sender_type = PedagogicalMessage.SenderType.LEARNER
            fake_message.message_type = PedagogicalMessage.MessageType.QUESTION
            fake_message.sequence_number = 1
            message_objects.create.return_value = fake_message

            message = service.add_message(
                session=session,
                sender_type=PedagogicalMessage.SenderType.LEARNER,
                message_type=PedagogicalMessage.MessageType.QUESTION,
                content="Why does this work?",
                sequence_number=1,
                metadata={"source": "learner"},
            )

        self.assertIs(message, fake_message)
        message_objects.create.assert_called_once_with(
            pedagogical_session=session,
            sender_type=PedagogicalMessage.SenderType.LEARNER,
            message_type=PedagogicalMessage.MessageType.QUESTION,
            content="Why does this work?",
            sequence_number=1,
            metadata={"source": "learner"},
        )
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "pedagogy.message_added")
        self.assertEqual(event.payload["sequence_number"], 1)

    def test_add_message_auto_assigns_next_sequence_number(self):
        service = PedagogicalSessionService(event_publisher=Mock())
        session = DummySession(status=PedagogicalState.ACTIVE)

        with patch("apps.learning.services.pedagogical_session_service.PedagogicalMessage.objects") as message_objects:
            message_objects.filter.return_value.aggregate.return_value = {"highest": 2}
            fake_message = Mock(spec=PedagogicalMessage)
            fake_message.id = "message-3"
            fake_message.sender_type = PedagogicalMessage.SenderType.ABBOT
            fake_message.message_type = PedagogicalMessage.MessageType.EXPLANATION
            fake_message.sequence_number = 3
            message_objects.create.return_value = fake_message

            service.add_message(
                session=session,
                sender_type=PedagogicalMessage.SenderType.ABBOT,
                message_type=PedagogicalMessage.MessageType.EXPLANATION,
                content="Here is the idea.",
            )

        message_objects.create.assert_called_once()
        self.assertEqual(message_objects.create.call_args.kwargs["sequence_number"], 3)

    def test_add_message_rejects_invalid_sequence_numbers(self):
        service = PedagogicalSessionService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.add_message(
                session=DummySession(status=PedagogicalState.ACTIVE),
                sender_type=PedagogicalMessage.SenderType.LEARNER,
                message_type=PedagogicalMessage.MessageType.RESPONSE,
                content="Answer",
                sequence_number=0,
            )

    def test_list_messages_orders_by_sequence_number(self):
        service = PedagogicalSessionService(event_publisher=Mock())
        session = DummySession(status=PedagogicalState.ACTIVE)
        expected_messages = [Mock(), Mock()]

        with patch("apps.learning.services.pedagogical_session_service.PedagogicalMessage.objects") as message_objects:
            message_objects.filter.return_value.order_by.return_value = expected_messages

            messages = service.list_messages(session)

        self.assertEqual(messages, expected_messages)
        message_objects.filter.assert_called_once_with(pedagogical_session=session)
        message_objects.filter.return_value.order_by.assert_called_once_with("sequence_number")


class PedagogicalEventRegistryTests(SimpleTestCase):
    def test_all_pedagogy_events_are_registered_for_discovery(self):
        expected_event_names = {
            "pedagogy.session_created",
            "pedagogy.session_started",
            "pedagogy.session_paused",
            "pedagogy.session_resumed",
            "pedagogy.session_completed",
            "pedagogy.session_abandoned",
            "pedagogy.message_added",
        }

        registered_event_names = set(default_event_registry._subscribers)

        self.assertTrue(expected_event_names.issubset(registered_event_names))
