from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.core.events import default_event_registry
from apps.learning.services.learning_companion_service import (
    CompanionInteractionType,
    CompanionType,
    LearningCompanionService,
)


class LearningCompanionServiceTests(SimpleTestCase):
    def test_companion_registration(self):
        publisher = Mock()
        service = LearningCompanionService(event_publisher=publisher, conversation_orchestrator=Mock())

        companion = service.register_companion(
            companion_type=CompanionType.STUDY_BUDDY,
            name="Study Buddy",
            description="A deterministic study companion.",
            supported_interaction_types=[CompanionInteractionType.ENCOURAGEMENT],
        )

        self.assertEqual(companion.companion_type, "study_buddy")
        self.assertEqual(companion.profile.name, "Study Buddy")
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "learning.companion_registered")

    def test_companion_retrieval(self):
        service = LearningCompanionService(event_publisher=Mock(), conversation_orchestrator=Mock())

        companion = service.get_companion(CompanionType.ARIEL)

        self.assertEqual(companion.companion_type, "ariel")
        self.assertEqual(companion.profile.name, "Ariel")

    def test_companion_listing(self):
        service = LearningCompanionService(event_publisher=Mock(), conversation_orchestrator=Mock())
        service.register_companion(CompanionType.STUDY_BUDDY, "Study Buddy")

        companions = service.list_companions()

        self.assertEqual([companion.companion_type for companion in companions], ["ariel", "study_buddy"])

    def test_activating_companion_for_session(self):
        publisher = Mock()
        service = LearningCompanionService(event_publisher=publisher, conversation_orchestrator=Mock())
        session = self._session()

        companion = service.activate_companion_for_session(session, CompanionType.ARIEL)

        self.assertEqual(companion.companion_type, "ariel")
        self.assertEqual(service.list_session_companions(session), [companion])
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "learning.companion_activated")

    def test_deactivating_companion_for_session(self):
        publisher = Mock()
        service = LearningCompanionService(event_publisher=publisher, conversation_orchestrator=Mock())
        session = self._session()
        service.activate_companion_for_session(session, CompanionType.ARIEL)

        service.deactivate_companion_for_session(session, CompanionType.ARIEL)

        self.assertEqual(service.list_session_companions(session), [])
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "learning.companion_deactivated")

    def test_listing_session_companions(self):
        service = LearningCompanionService(event_publisher=Mock(), conversation_orchestrator=Mock())
        session = self._session()

        service.activate_companion_for_session(session, CompanionType.ARIEL)

        self.assertEqual([companion.companion_type for companion in service.list_session_companions(session)], ["ariel"])

    def test_ariel_deterministic_presence_response(self):
        response = self._service().generate_companion_response(
            self._session(),
            CompanionType.ARIEL,
            CompanionInteractionType.PRESENCE,
        )

        self.assertEqual(response.content, "I'm here with you. Let's stay focused on this learning moment.")

    def test_ariel_deterministic_encouragement_response(self):
        response = self._service().generate_companion_response(
            self._session(),
            CompanionType.ARIEL,
            CompanionInteractionType.ENCOURAGEMENT,
        )

        self.assertEqual(
            response.content,
            "You're making progress. Take the next step carefully and keep your reasoning visible.",
        )

    def test_ariel_deterministic_reflection_prompt(self):
        response = self._service().generate_companion_response(
            self._session(),
            CompanionType.ARIEL,
            CompanionInteractionType.REFLECTION_PROMPT,
        )

        self.assertEqual(
            response.content,
            "Pause for a moment: what part of this concept feels clearest, and what still feels uncertain?",
        )

    def test_ariel_deterministic_session_summary(self):
        response = self._service().generate_companion_response(
            self._session(),
            CompanionType.ARIEL,
            CompanionInteractionType.SESSION_SUMMARY,
        )

        self.assertEqual(
            response.content,
            "Session reflection: you engaged with the concept and preserved a path for the next learning step.",
        )

    def test_companion_response_recorded_in_session_conversation(self):
        conversation = Mock()
        service = LearningCompanionService(event_publisher=Mock(), conversation_orchestrator=conversation)
        session = self._session()

        response = service.generate_companion_response(session, CompanionType.ARIEL, CompanionInteractionType.PRESENCE)

        self.assertTrue(response.recorded)
        conversation.add_turn.assert_called_once_with(
            session=session,
            sender_type="ariel",
            message_type="presence",
            content="I'm here with you. Let's stay focused on this learning moment.",
        )

    def test_companion_does_not_modify_academic_content(self):
        service = self._service()
        session = self._session()
        session.content_concept.save = Mock()
        session.content_concept.content_section.save = Mock()
        session.content_concept.content_section.learning_resource.save = Mock()

        service.generate_companion_response(session, CompanionType.ARIEL, CompanionInteractionType.REFLECTION_PROMPT)

        self.assertEqual(session.content_concept.title, "Opportunity Cost")
        self.assertEqual(session.content_concept.content_section.title, "Economic Choices")
        self.assertEqual(session.content_concept.content_section.learning_resource.title, "Economics Guide")
        session.content_concept.save.assert_not_called()
        session.content_concept.content_section.save.assert_not_called()
        session.content_concept.content_section.learning_resource.save.assert_not_called()

    def test_events_are_published(self):
        publisher = Mock()
        service = LearningCompanionService(event_publisher=publisher, conversation_orchestrator=Mock())
        session = self._session()

        service.register_companion(CompanionType.STUDY_BUDDY, "Study Buddy")
        service.activate_companion_for_session(session, CompanionType.ARIEL)
        service.generate_companion_response(session, CompanionType.ARIEL, CompanionInteractionType.PRESENCE)
        service.deactivate_companion_for_session(session, CompanionType.ARIEL)

        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            [
                "learning.companion_registered",
                "learning.companion_activated",
                "learning.companion_response_generated",
                "learning.companion_deactivated",
            ],
        )

    def test_companion_events_are_registered_for_discovery(self):
        registered_event_names = set(default_event_registry._subscribers)

        self.assertIn("learning.companion_registered", registered_event_names)
        self.assertIn("learning.companion_activated", registered_event_names)
        self.assertIn("learning.companion_deactivated", registered_event_names)
        self.assertIn("learning.companion_response_generated", registered_event_names)

    def _service(self):
        return LearningCompanionService(event_publisher=Mock(), conversation_orchestrator=Mock())

    def _session(self):
        return SimpleNamespace(id="session-1", content_concept=self._academic_concept())

    def _academic_concept(self):
        resource = SimpleNamespace(id="resource-1", title="Economics Guide")
        section = SimpleNamespace(id="section-1", title="Economic Choices", learning_resource=resource)
        return SimpleNamespace(id="concept-1", title="Opportunity Cost", content_section=section)
