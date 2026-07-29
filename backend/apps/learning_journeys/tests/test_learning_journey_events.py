from django.test import SimpleTestCase

from apps.core.events.registry import default_event_registry


class LearningJourneyEventRegistryTests(SimpleTestCase):
    def test_learning_journey_events_are_registered(self):
        for event_name in [
            "learning_journey.created",
            "learning_journey.synchronized",
            "learning_journey.state_changed",
            "learning_journey.paused",
            "learning_journey.resumed",
            "learning_journey.withdrawn",
            "learning_journey.archived",
            "learning_journey.action_accepted",
            "learning_journey.action_succeeded",
            "learning_journey.action_failed",
            "learning_journey.action_rejected",
            "learning_journey.intent_confirmed",
            "learning_journey.curriculum_resolution_requested",
            "learning_journey.curriculum_selected",
            "learning_journey.diagnostic_started",
            "learning_journey.placement_confirmed",
            "learning_journey.bridge_plan_requested",
            "learning_journey.learning_plan_created",
            "learning_journey.learning_plan_activated",
            "learning_journey.teaching_prepared",
            "learning_journey.teaching_session_started",
        ]:
            self.assertIn(event_name, default_event_registry._subscribers)
