from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.academic.domain.models import ContentConcept
from apps.assessments.domain.models import LearningEvidenceType
from apps.remediation.application import (
    RecommendationService,
    RemediationExecutionService,
    RemediationHistoryService,
    RemediationPlanningService,
)
from apps.remediation.domain.models import RemediationOutcomeValue, RemediationPlan, RemediationPlanStatus, RemediationRecommendationType
from apps.users.domain.models import User


class RemediationApplicationServiceTests(SimpleTestCase):
    def test_recommendation_service_maps_evidence_patterns(self):
        evidence = self._evidence(LearningEvidenceType.MISCONCEPTION)

        recommendations = RecommendationService().recommendations_for_evidence(evidence)

        self.assertIn(RemediationRecommendationType.REVIEW_LESSON, {item.recommendation_type for item in recommendations})
        self.assertIn(RemediationRecommendationType.EDUCATOR_REVIEW, {item.recommendation_type for item in recommendations})

    def test_planning_service_builds_plan_and_recommendations(self):
        plan_repo = Mock()
        recommendation_repo = Mock()
        activity_repo = Mock()
        publisher = Mock()
        plan_repo.add.side_effect = lambda plan: self._with_ids(plan)
        recommendation_repo.add.side_effect = lambda recommendation: self._with_ids(recommendation)
        activity_repo.add.side_effect = lambda activity: self._with_ids(activity)
        service = RemediationPlanningService(
            plan_repository=plan_repo,
            recommendation_repository=recommendation_repo,
            activity_repository=activity_repo,
            event_publisher=publisher,
        )

        plan = service.plan_from_evidence(self._evidence(LearningEvidenceType.PARTIAL_UNDERSTANDING))

        self.assertIsNotNone(plan)
        self.assertTrue(recommendation_repo.add.called)
        self.assertTrue(activity_repo.add.called)
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "remediation.planned")

    def test_planning_service_skips_positive_evidence(self):
        service = RemediationPlanningService(
            plan_repository=Mock(),
            recommendation_repository=Mock(),
            activity_repository=Mock(),
            event_publisher=Mock(),
        )

        self.assertIsNone(service.plan_from_evidence(self._evidence(LearningEvidenceType.CORRECT_RESPONSE, confidence=0.9)))

    def test_execution_service_lifecycle(self):
        plan_repo = Mock()
        publisher = Mock()
        plan_repo.save.side_effect = lambda plan: plan
        service = RemediationExecutionService(plan_repository=plan_repo, event_publisher=publisher)
        plan = self._plan()

        service.start_remediation(plan)
        service.complete_remediation(plan)
        service.close_remediation(plan)

        self.assertEqual(plan.status, RemediationPlanStatus.CLOSED)
        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            ["remediation.started", "remediation.completed", "remediation.closed"],
        )

    def test_execution_service_records_escalated_outcome(self):
        plan_repo = Mock()
        outcome_repo = Mock()
        publisher = Mock()
        plan_repo.save.side_effect = lambda plan: plan
        outcome_repo.add.side_effect = lambda outcome: outcome
        service = RemediationExecutionService(plan_repository=plan_repo, outcome_repository=outcome_repo, event_publisher=publisher)
        plan = self._plan()

        outcome = service.record_outcome(plan, RemediationOutcomeValue.ESCALATED)

        self.assertEqual(outcome.outcome, RemediationOutcomeValue.ESCALATED)
        self.assertEqual(plan.status, RemediationPlanStatus.ESCALATED)

    def test_history_service_timeline(self):
        plan_repo = Mock()
        activity_repo = Mock()
        outcome_repo = Mock()
        plan = self._plan()
        activity = SimpleNamespace(title="Replay lesson", activity_type="lesson_replay", status="planned", created_at=2)
        outcome = SimpleNamespace(outcome="improved", notes="", recorded_at=3)
        activity_repo.list_for_plan.return_value = [activity]
        outcome_repo.list_for_plan.return_value = [outcome]

        timeline = RemediationHistoryService(plan_repo, activity_repo, outcome_repo).timeline_for_plan(plan)

        self.assertEqual([entry.event_type for entry in timeline], ["plan_created", "activity_created", "outcome_recorded"])

    def _evidence(self, evidence_type, confidence=0.7):
        learner = User(id="learner-1")
        concept = ContentConcept(id="concept-1")
        return SimpleNamespace(
            id="evidence-1",
            learner=learner,
            learner_id="learner-1",
            content_concept=concept,
            content_concept_id="concept-1",
            source_type="assessment_evaluation",
            source_id="source-1",
            evidence_type=evidence_type,
            confidence=confidence,
        )

    def _plan(self):
        plan = RemediationPlan(status=RemediationPlanStatus.PENDING)
        plan.id = "plan-1"
        plan.learner_id = "learner-1"
        plan.content_concept_id = "concept-1"
        plan.created_at = 1
        return plan

    def _with_ids(self, obj):
        obj.id = getattr(obj, "id", "id-1")
        obj.learner_id = getattr(getattr(obj, "learner", None), "id", "learner-1")
        obj.content_concept_id = getattr(getattr(obj, "content_concept", None), "id", "concept-1")
        return obj
