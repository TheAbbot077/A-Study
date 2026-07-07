from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.core.events import default_event_registry
from apps.learning.services import ConversationOrchestratorService
from apps.learning.services.conversation_orchestrator_service import ConversationInteractionType


class ConversationOrchestratorServiceTests(SimpleTestCase):
    def test_conversation_initialization(self):
        publisher = Mock()
        session_service = Mock()
        session_service.list_messages.return_value = []
        service = ConversationOrchestratorService(event_publisher=publisher, session_service=session_service)

        context = service.initialize_conversation(self._session())

        self.assertEqual(context.current_turn_number, 0)
        self.assertEqual(context.active_conversation_window.turns, [])
        self.assertIsNotNone(context.grounded_teaching_package)
        self.assertIsNotNone(context.instructional_strategy)
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "learning.conversation_initialized")

    def test_adding_conversation_turns(self):
        publisher = Mock()
        session_service = Mock()
        session_service.add_message.return_value = self._message(
            sequence_number=1,
            sender_type="learner",
            message_type="learner_question",
            content="Why does this work?",
        )
        service = ConversationOrchestratorService(event_publisher=publisher, session_service=session_service)

        turn = service.add_turn(self._session(), "learner", "learner_question", "Why does this work?")

        self.assertEqual(turn.sequence_number, 1)
        self.assertEqual(turn.sender_type, "learner")
        self.assertEqual(turn.message_type, "learner_question")
        session_service.add_message.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "learning.turn_added")

    def test_ordering_preserved(self):
        messages = [
            self._message(1, "abbot", "explanation", "First"),
            self._message(2, "learner", "learner_question", "Second"),
            self._message(3, "abbot", "clarification", "Third"),
        ]
        service = self._service_with_messages(messages)

        turns = service.list_conversation_turns(self._session())

        self.assertEqual([turn.content for turn in turns], ["First", "Second", "Third"])
        self.assertEqual([turn.sequence_number for turn in turns], [1, 2, 3])

    def test_window_trimming(self):
        messages = [
            self._message(1, "abbot", "explanation", "First"),
            self._message(2, "learner", "reflection", "Second"),
            self._message(3, "abbot", "transition", "Third"),
            self._message(4, "learner", "learner_question", "Fourth"),
        ]
        publisher = Mock()
        service = self._service_with_messages(messages, publisher=publisher)

        window = service.trim_conversation_window(self._session(), max_turns=2)

        self.assertEqual([turn.sequence_number for turn in window.turns], [3, 4])
        self.assertEqual(window.window_size, 2)
        self.assertTrue(window.supports_future_summarization)
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "learning.window_trimmed")

    def test_current_turn_tracking(self):
        service = self._service_with_messages(
            [
                self._message(1, "abbot", "explanation", "First"),
                self._message(2, "learner", "reflection", "Second"),
            ]
        )

        context = service.build_conversation_context(self._session())

        self.assertEqual(context.current_turn_number, 2)
        self.assertEqual(context.current_instructional_step.sequence_number, 3)

    def test_expected_interaction_calculation(self):
        empty_service = self._service_with_messages([])
        question_service = self._service_with_messages([self._message(1, "learner", "learner_question", "Question")])
        abbot_service = self._service_with_messages([self._message(1, "abbot", "explanation", "Explanation")])

        self.assertEqual(empty_service.next_expected_interaction(self._session()), ConversationInteractionType.EXPLANATION)
        self.assertEqual(question_service.next_expected_interaction(self._session()), ConversationInteractionType.CLARIFICATION)
        self.assertEqual(abbot_service.next_expected_interaction(self._session()), ConversationInteractionType.REFLECTION)

    def test_deterministic_behaviour(self):
        messages = [
            self._message(1, "abbot", "explanation", "First"),
            self._message(2, "learner", "reflection", "Second"),
        ]
        service = self._service_with_messages(messages)

        first_context = service.build_conversation_context(self._session())
        second_context = service.build_conversation_context(self._session())

        self.assertEqual(first_context.active_conversation_window, second_context.active_conversation_window)
        self.assertEqual(first_context.current_turn_number, second_context.current_turn_number)
        self.assertEqual(first_context.current_instructional_step, second_context.current_instructional_step)

    def test_event_publication(self):
        publisher = Mock()
        session_service = Mock()
        session_service.list_messages.return_value = []
        session_service.add_message.return_value = self._message(1, "abbot", "explanation", "Hello")
        service = ConversationOrchestratorService(event_publisher=publisher, session_service=session_service)

        service.initialize_conversation(self._session())
        service.add_turn(self._session(), "abbot", "explanation", "Hello")
        service.trim_conversation_window(self._session(), max_turns=1)

        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            ["learning.conversation_initialized", "learning.turn_added", "learning.window_trimmed"],
        )

    def test_conversation_events_are_registered_for_discovery(self):
        registered_event_names = set(default_event_registry._subscribers)

        self.assertIn("learning.conversation_initialized", registered_event_names)
        self.assertIn("learning.turn_added", registered_event_names)
        self.assertIn("learning.window_trimmed", registered_event_names)

    def test_academic_content_remains_unchanged(self):
        session = self._session()
        session.content_concept.save = Mock()
        session.content_concept.content_section.save = Mock()
        session.content_concept.content_section.learning_resource.save = Mock()
        service = self._service_with_messages([])

        service.initialize_conversation(session)

        self.assertEqual(session.content_concept.title, "Opportunity Cost")
        self.assertEqual(session.content_concept.content_section.title, "Economic Choices")
        self.assertEqual(session.content_concept.content_section.learning_resource.title, "Economics Guide")
        session.content_concept.save.assert_not_called()
        session.content_concept.content_section.save.assert_not_called()
        session.content_concept.content_section.learning_resource.save.assert_not_called()

    def test_interaction_types_are_supported(self):
        self.assertEqual(
            ConversationInteractionType.VALUES,
            {
                "explanation",
                "learner_question",
                "clarification",
                "acknowledgement",
                "reflection",
                "summary",
                "transition",
                "system",
            },
        )

    def _service_with_messages(self, messages, publisher=None):
        session_service = Mock()
        session_service.list_messages.return_value = messages
        return ConversationOrchestratorService(
            event_publisher=publisher or Mock(),
            session_service=session_service,
        )

    def _message(self, sequence_number, sender_type, message_type, content):
        return SimpleNamespace(
            sequence_number=sequence_number,
            sender_type=sender_type,
            message_type=message_type,
            content=content,
            created_at=datetime(2026, 7, 7, 12, sequence_number, tzinfo=timezone.utc),
            metadata={},
        )

    def _session(self):
        return SimpleNamespace(id="session-1", learner=SimpleNamespace(id="learner-1"), content_concept=self._academic_concept())

    def _academic_concept(self):
        subject = SimpleNamespace(id="subject-1", name="Economics")
        curriculum = SimpleNamespace(id="curriculum-1", name="Intro Economics")
        curriculum_unit = SimpleNamespace(id="unit-1", title="Scarcity", sequence_number=1)
        resource = SimpleNamespace(
            id="resource-1",
            title="Economics Guide",
            resource_type="guide",
            subject=subject,
            curriculum=curriculum,
            curriculum_unit=curriculum_unit,
        )
        section = SimpleNamespace(
            id="section-1",
            title="Economic Choices",
            sequence_number=1,
            review_status="approved",
            quality_status="high",
            learning_resource=resource,
        )
        return SimpleNamespace(
            id="concept-1",
            title="Opportunity Cost",
            description="The value of the next best alternative.",
            learning_objective="Explain opportunity cost.",
            sequence_number=2,
            review_status="approved",
            quality_status="high",
            content_section=section,
        )
