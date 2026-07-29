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
        ]:
            self.assertIn(event_name, default_event_registry._subscribers)
