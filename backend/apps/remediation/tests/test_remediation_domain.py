from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.remediation.domain.models import (
    RemediationActivity,
    RemediationActivityStatus,
    RemediationOutcome,
    RemediationOutcomeValue,
    RemediationPlan,
    RemediationPlanStatus,
    RemediationRecommendation,
)


class RemediationDomainTests(SimpleTestCase):
    def test_lifecycle_transitions(self):
        plan = RemediationPlan(status=RemediationPlanStatus.PENDING)

        plan.activate()
        self.assertEqual(plan.status, RemediationPlanStatus.ACTIVE)
        plan.complete()
        self.assertEqual(plan.status, RemediationPlanStatus.COMPLETED)
        plan.close()
        self.assertEqual(plan.status, RemediationPlanStatus.CLOSED)

    def test_invalid_lifecycle_transition_rejected(self):
        plan = RemediationPlan(status=RemediationPlanStatus.CLOSED)

        with self.assertRaises(ValueError):
            plan.activate()

    def test_recommendation_creation(self):
        recommendation = RemediationRecommendation(title="Review", priority=2)

        recommendation.raise_priority()

        self.assertEqual(recommendation.priority, 1)

    def test_activity_creation_and_completion(self):
        activity = RemediationActivity(status=RemediationActivityStatus.PLANNED)

        activity.start()
        activity.complete(evidence_reference_id="evidence-1")

        self.assertEqual(activity.status, RemediationActivityStatus.COMPLETED)
        self.assertEqual(activity.evidence_reference_id, "evidence-1")

    def test_outcome_recording(self):
        outcome = RemediationOutcome(outcome=RemediationOutcomeValue.ESCALATED)

        self.assertTrue(outcome.requires_escalation())
