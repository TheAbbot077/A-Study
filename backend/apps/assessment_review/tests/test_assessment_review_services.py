from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.assessment_review.application import (
    AssessmentAnalyticsService,
    AssessmentReviewService,
    DifficultyCalibrationService,
    QuestionReviewService,
    ReviewerAssignmentService,
)
from apps.academic.domain.models import ContentConcept
from apps.assessment_review.domain.models import ReviewDecisionValue, ReviewStatus
from apps.assessments.domain.models import Assessment, AssessmentItemType, ItemBankEntry
from apps.core.events import default_event_registry


class AssessmentReviewServiceTests(SimpleTestCase):
    def test_assessment_review_service_starts_and_approves_review(self):
        review_repository = Mock()
        finding_repository = Mock()
        decision_repository = Mock()
        publisher = Mock()
        review_repository.add.side_effect = lambda review: self._with_ids(review, assessment_id="assessment-1")
        review_repository.save.side_effect = lambda review: self._with_ids(review, assessment_id="assessment-1")
        decision_repository.add.side_effect = lambda decision: self._with_ids(decision)
        service = AssessmentReviewService(
            review_repository=review_repository,
            finding_repository=finding_repository,
            decision_repository=decision_repository,
            event_publisher=publisher,
        )

        review = service.open_review(self._assessment("assessment-1"))
        review = service.start_review(review)
        decision = service.approve_review(review)

        self.assertEqual(review.status, ReviewStatus.APPROVED)
        self.assertEqual(decision.decision, ReviewDecisionValue.APPROVED)
        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            ["assessment_review.started", "assessment_review.assessment_approved"],
        )

    def test_question_review_service_records_decision_event(self):
        review_repository = Mock()
        decision_repository = Mock()
        review_repository.add.side_effect = lambda review: self._with_ids(review, item_bank_entry_id="item-1")
        review_repository.save.side_effect = lambda review: self._with_ids(review, item_bank_entry_id="item-1")
        decision_repository.add.side_effect = lambda decision: self._with_ids(decision)
        publisher = Mock()
        service = QuestionReviewService(
            review_repository=review_repository,
            finding_repository=Mock(),
            decision_repository=decision_repository,
            event_publisher=publisher,
        )

        review = service.open_review(self._item("item-1"))
        review = service.start_review(review)
        service.record_decision(review, ReviewDecisionValue.NEEDS_REVISION)

        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment_review.question_reviewed")

    def test_calibration_service_publishes_event(self):
        calibration_repository = Mock()
        calibration_repository.add.side_effect = lambda calibration: self._with_ids(calibration)
        publisher = Mock()
        service = DifficultyCalibrationService(
            calibration_repository=calibration_repository,
            event_publisher=publisher,
        )

        calibration = service.calibrate_item(self._item("item-1", difficulty="medium"), observed_success_rate=0.9, sample_size=10)

        self.assertEqual(calibration.direction, "easier_than_expected")
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment_review.difficulty_calibrated")

    def test_assignment_service_reports_workload(self):
        assignment_repository = Mock()
        assignment_repository.list_active_for_reviewer.return_value = [Mock(), Mock()]
        service = ReviewerAssignmentService(assignment_repository=assignment_repository)

        workload = service.reviewer_workload(SimpleNamespace(id="reviewer-1"))

        self.assertEqual(workload["active_assignment_count"], 2)

    def test_analytics_service_aggregates_metrics(self):
        assessment = self._assessment("assessment-1")
        review = SimpleNamespace(
            opened_at=datetime(2026, 1, 1, 12, 0, 0),
            completed_at=datetime(2026, 1, 1, 12, 10, 0),
            decisions=SimpleNamespace(all=lambda: [SimpleNamespace(decision=ReviewDecisionValue.APPROVED)]),
        )
        result = SimpleNamespace(percentage=80.0, passed=True)

        with patch("apps.assessment_review.application.analytics_service.AssessmentResult.objects") as result_objects:
            with patch("apps.assessment_review.application.analytics_service.AssessmentReview.objects") as review_objects:
                result_objects.filter.return_value = [result]
                review_objects.filter.side_effect = lambda **kwargs: [review] if "assessment" in kwargs else SimpleNamespace(count=lambda: 1)
                metrics = AssessmentAnalyticsService().assessment_metrics(assessment)

        self.assertEqual(metrics["attempt_count"], 1)
        self.assertEqual(metrics["pass_rate"], 1.0)
        self.assertEqual(metrics["approval_rate"], 1.0)

    def test_event_registry_contains_assessment_review_events(self):
        expected = {
            "assessment_review.started",
            "assessment_review.question_reviewed",
            "assessment_review.difficulty_calibrated",
            "assessment_review.assessment_approved",
            "assessment_review.assessment_rejected",
            "assessment_review.assessment_needs_revision",
        }

        self.assertTrue(expected.issubset(set(default_event_registry._subscribers)))

    def _assessment(self, id):
        return Assessment(
            id=id,
            title="Assessment",
            content_concept=ContentConcept(id="concept-1", title="Concept"),
        )

    def _item(self, id, difficulty="medium"):
        return ItemBankEntry(
            id=id,
            content_concept=ContentConcept(id="concept-1", title="Concept"),
            item_type=AssessmentItemType.MULTIPLE_CHOICE,
            prompt="Prompt",
            difficulty=difficulty,
        )

    def _with_ids(self, obj, **attrs):
        obj.id = getattr(obj, "id", "id-1")
        for key, value in attrs.items():
            setattr(obj, key, value)
        return obj
