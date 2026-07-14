from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.remediation.domain.models import RemediationActivity, RemediationOutcome, RemediationPlan, RemediationRecommendation
from apps.remediation.infrastructure.persistence.repositories import (
    DjangoActivityRepository,
    DjangoOutcomeRepository,
    DjangoRecommendationRepository,
    DjangoRemediationPlanRepository,
)


class RemediationRepositoryTests(SimpleTestCase):
    def test_plan_repository_crud_behavior(self):
        repository = DjangoRemediationPlanRepository()
        plan = Mock(spec=RemediationPlan)

        repository.add(plan)
        repository.save(plan)

        self.assertEqual(plan.save.call_count, 2)

    def test_plan_repository_lists_by_business_intent(self):
        repository = DjangoRemediationPlanRepository()
        learner = Mock()
        expected = [Mock(spec=RemediationPlan)]

        with patch("apps.remediation.infrastructure.persistence.repositories.RemediationPlan.objects") as plan_objects:
            plan_objects.filter.return_value.order_by.return_value = expected
            plans = repository.list_for_learner(learner)

        self.assertEqual(plans, expected)
        plan_objects.filter.assert_called_once_with(learner=learner)

    def test_recommendation_repository_mapping(self):
        repository = DjangoRecommendationRepository()
        recommendation = Mock(spec=RemediationRecommendation)

        repository.add(recommendation)

        recommendation.save.assert_called_once()

    def test_activity_repository_mapping(self):
        repository = DjangoActivityRepository()
        activity = Mock(spec=RemediationActivity)

        repository.add(activity)
        repository.save(activity)

        self.assertEqual(activity.save.call_count, 2)

    def test_outcome_repository_mapping(self):
        repository = DjangoOutcomeRepository()
        outcome = Mock(spec=RemediationOutcome)

        repository.add(outcome)

        outcome.save.assert_called_once()
