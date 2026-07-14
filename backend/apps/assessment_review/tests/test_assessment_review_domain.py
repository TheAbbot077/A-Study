from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.academic.domain.models import ContentConcept
from apps.assessment_review.domain.models import (
    AssessmentReview,
    CalibrationDirection,
    QualityFinding,
    QuestionReview,
    ReviewStatus,
    ReviewerAssignment,
    ReviewerAssignmentStatus,
)
from apps.assessments.domain.models import Assessment, AssessmentItemType, ItemBankEntry
from apps.assessment_review.domain.services import RuleBasedDifficultyCalibrationPolicy
from apps.assessments.domain.models import ItemDifficulty
from apps.users.domain.models import User


class AssessmentReviewDomainTests(SimpleTestCase):
    def test_assessment_review_lifecycle_transitions(self):
        review = AssessmentReview(status=ReviewStatus.DRAFT)

        review.transition_to(ReviewStatus.PENDING_REVIEW)
        review.transition_to(ReviewStatus.IN_REVIEW)
        review.transition_to(ReviewStatus.APPROVED)

        self.assertEqual(review.status, ReviewStatus.APPROVED)
        self.assertIsNotNone(review.started_at)
        self.assertIsNotNone(review.completed_at)

    def test_question_review_rejects_invalid_transition(self):
        review = QuestionReview(status=ReviewStatus.APPROVED)

        with self.assertRaises(ValueError):
            review.transition_to(ReviewStatus.IN_REVIEW)

    def test_quality_finding_can_be_resolved(self):
        finding = QualityFinding(resolved=False)

        finding.resolve()

        self.assertTrue(finding.resolved)

    def test_quality_finding_requires_exactly_one_review_target(self):
        finding = QualityFinding()

        with self.assertRaises(ValidationError):
            finding.clean()

    def test_reviewer_assignment_reassign_and_complete(self):
        reviewer = User(id="reviewer-1", email="reviewer1@example.com")
        assignment = ReviewerAssignment(
            reviewer=reviewer,
            assessment_review=AssessmentReview(assessment=self._assessment("assessment-1")),
            status=ReviewerAssignmentStatus.ASSIGNED,
        )

        assignment.reassign(User(id="reviewer-2", email="reviewer2@example.com"))
        assignment.complete()

        self.assertEqual(assignment.status, ReviewerAssignmentStatus.COMPLETED)
        self.assertIsNotNone(assignment.completed_at)

    def test_reviewer_assignment_requires_exactly_one_review_target(self):
        reviewer = User(id="reviewer-1", email="reviewer1@example.com")
        assignment = ReviewerAssignment(reviewer=reviewer)

        with self.assertRaises(ValidationError):
            assignment.clean()

    def test_rule_based_calibration_policy(self):
        policy = RuleBasedDifficultyCalibrationPolicy()

        easier = policy.calibrate(ItemDifficulty.MEDIUM, observed_success_rate=0.9, sample_size=10)
        harder = policy.calibrate(ItemDifficulty.MEDIUM, observed_success_rate=0.2, sample_size=10)
        insufficient = policy.calibrate(ItemDifficulty.MEDIUM, observed_success_rate=None, sample_size=1)

        self.assertEqual(easier.direction, CalibrationDirection.EASIER_THAN_EXPECTED)
        self.assertEqual(harder.direction, CalibrationDirection.HARDER_THAN_EXPECTED)
        self.assertEqual(insufficient.direction, CalibrationDirection.INSUFFICIENT_DATA)

    def _assessment(self, id):
        return Assessment(
            id=id,
            title="Assessment",
            content_concept=ContentConcept(id="concept-1", title="Concept"),
        )
