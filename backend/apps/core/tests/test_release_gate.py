from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.release_gate import EvaluateBackendReleaseGateService


class BackendReleaseGateServiceTests(SimpleTestCase):
    def test_release_gate_reports_combined_readiness(self):
        learning_journey = {
            "result": "READY_WITH_WARNINGS",
            "blockers": [],
            "warnings": [{"code": "JOURNEY_WARNING"}],
            "summary": {"learning_journey": True},
        }
        learning_experience = {
            "result": "READY",
            "blockers": [],
            "warnings": [],
            "summary": {"learning_experience": True},
        }

        with patch(
            "apps.learning_journeys.application.release_readiness.LearningJourneyReleaseReadinessService.report",
            return_value=learning_journey,
        ), patch(
            "apps.learning_journeys.application.learning_experience_release_readiness.EvaluateLearningExperienceReleaseReadinessService.report",
            return_value=learning_experience,
        ), patch(
            "apps.core.services.release_gate.BusinessEventDelivery.objects.filter"
        ) as delivery_filter:
            delivery_filter.return_value.count.return_value = 0
            report = EvaluateBackendReleaseGateService().report()

        self.assertEqual(report["result"], "READY_WITH_WARNINGS")
        self.assertTrue(any(item["code"] == "LEARNING_JOURNEY_WARNINGS" for item in report["warnings"]))
        self.assertIn("learning_journey_result", report["summary"])

    def test_release_gate_blocks_on_domain_not_ready(self):
        learning_journey = {
            "result": "NOT_READY",
            "blockers": [{"code": "JOURNEY_BLOCKER"}],
            "warnings": [],
            "summary": {},
        }
        learning_experience = {
            "result": "READY",
            "blockers": [],
            "warnings": [],
            "summary": {},
        }

        with patch(
            "apps.learning_journeys.application.release_readiness.LearningJourneyReleaseReadinessService.report",
            return_value=learning_journey,
        ), patch(
            "apps.learning_journeys.application.learning_experience_release_readiness.EvaluateLearningExperienceReleaseReadinessService.report",
            return_value=learning_experience,
        ), patch(
            "apps.core.services.release_gate.BusinessEventDelivery.objects.filter"
        ) as delivery_filter:
            delivery_filter.return_value.count.return_value = 0
            report = EvaluateBackendReleaseGateService().report()

        self.assertEqual(report["result"], "NOT_READY")
        self.assertTrue(any(item["code"] == "RELEASE_GATE_BLOCKED" for item in report["blockers"]))
