from django.test import SimpleTestCase

from apps.core.events import default_event_registry
from apps.learning.domain.models import PedagogicalMessage


class PedagogicalArchitectureTests(SimpleTestCase):
    def test_all_pedagogical_events_are_registered_for_discovery(self):
        expected_event_names = {
            "pedagogy.session_created",
            "pedagogy.session_started",
            "pedagogy.session_paused",
            "pedagogy.session_resumed",
            "pedagogy.session_completed",
            "pedagogy.session_abandoned",
            "pedagogy.message_added",
            "learning.context_assembled",
            "learning.grounding_package_created",
            "learning.grounding_validated",
            "learning.strategy_selected",
            "learning.strategy_validated",
            "learning.conversation_initialized",
            "learning.turn_added",
            "learning.window_trimmed",
            "learning.abbot_request_prepared",
            "learning.abbot_response_generated",
            "learning.abbot_response_validated",
            "learning.companion_registered",
            "learning.companion_activated",
            "learning.companion_deactivated",
            "learning.companion_response_generated",
        }

        registered_event_names = set(default_event_registry._subscribers)

        self.assertTrue(expected_event_names.issubset(registered_event_names))

    def test_pedagogical_message_types_cover_pipeline_interactions(self):
        expected_message_types = {
            "explanation",
            "question",
            "response",
            "clarification",
            "summary",
            "learner_question",
            "acknowledgement",
            "reflection",
            "transition",
            "presence",
            "encouragement",
            "reflection_prompt",
            "clarification_prompt",
            "learning_check",
            "session_summary",
            "system",
        }

        message_types = {choice[0] for choice in PedagogicalMessage.MessageType.choices}

        self.assertTrue(expected_message_types.issubset(message_types))
