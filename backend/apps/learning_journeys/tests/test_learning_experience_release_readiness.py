import json

from django.core.management import call_command
from django.test import TestCase

from apps.core.events.registry import default_event_registry
from apps.learning_journeys.application.learning_experience_release_readiness import EvaluateLearningExperienceReleaseReadinessService, REQUIRED_LEARNING_EXPERIENCE_EVENTS


class LearningExperienceReleaseReadinessTests(TestCase):
    def test_release_readiness_reports_expected_shape(self):
        report = EvaluateLearningExperienceReleaseReadinessService().report()

        self.assertIn(report["result"], {"READY", "READY_WITH_WARNINGS", "NOT_READY"})
        self.assertIn("summary", report)
        self.assertIn("installed_apps_checked", report["summary"])
        self.assertIn("registered_event_count", report["summary"])
        for event_name in REQUIRED_LEARNING_EXPERIENCE_EVENTS:
            self.assertIn(event_name, default_event_registry._subscribers)

    def test_management_command_is_non_mutating(self):
        before = json.dumps(EvaluateLearningExperienceReleaseReadinessService().report(), sort_keys=True)

        call_command("report_learning_experience_release_readiness")

        after = json.dumps(EvaluateLearningExperienceReleaseReadinessService().report(), sort_keys=True)
        self.assertEqual(before, after)
