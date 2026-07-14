from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.assessment_review.domain.models import AssessmentReview, DifficultyCalibration, QuestionReview, ReviewerAssignment
from apps.assessment_review.infrastructure.persistence.repositories import (
    DjangoAssessmentReviewRepository,
    DjangoCalibrationRepository,
    DjangoQuestionReviewRepository,
    DjangoReviewerAssignmentRepository,
)


class AssessmentReviewRepositoryTests(SimpleTestCase):
    def test_assessment_review_repository_crud_behavior(self):
        repository = DjangoAssessmentReviewRepository()
        review = Mock(spec=AssessmentReview)

        repository.add(review)
        repository.save(review)

        self.assertEqual(review.save.call_count, 2)

    def test_assessment_review_repository_lists_pending_reviews(self):
        repository = DjangoAssessmentReviewRepository()
        expected = [Mock(spec=AssessmentReview)]

        with patch("apps.assessment_review.infrastructure.persistence.repositories.AssessmentReview.objects") as review_objects:
            review_objects.filter.return_value.order_by.return_value = expected
            reviews = repository.list_pending()

        self.assertEqual(reviews, expected)

    def test_question_review_repository_lists_by_reviewer(self):
        repository = DjangoQuestionReviewRepository()
        reviewer = Mock()
        expected = [Mock(spec=QuestionReview)]

        with patch("apps.assessment_review.infrastructure.persistence.repositories.QuestionReview.objects") as review_objects:
            review_objects.filter.return_value.order_by.return_value = expected
            reviews = repository.list_for_reviewer(reviewer)

        self.assertEqual(reviews, expected)
        review_objects.filter.assert_called_once_with(reviewer=reviewer)

    def test_calibration_repository_lists_recent(self):
        repository = DjangoCalibrationRepository()
        expected = [Mock(spec=DifficultyCalibration)]

        with patch("apps.assessment_review.infrastructure.persistence.repositories.DifficultyCalibration.objects") as calibration_objects:
            calibration_objects.order_by.return_value.__getitem__.return_value = expected
            calibrations = repository.list_recent(limit=10)

        self.assertEqual(calibrations, expected)

    def test_assignment_repository_lists_active_for_reviewer(self):
        repository = DjangoReviewerAssignmentRepository()
        reviewer = Mock()
        expected = [Mock(spec=ReviewerAssignment)]

        with patch("apps.assessment_review.infrastructure.persistence.repositories.ReviewerAssignment.objects") as assignment_objects:
            assignment_objects.filter.return_value.exclude.return_value.order_by.return_value = expected
            assignments = repository.list_active_for_reviewer(reviewer)

        self.assertEqual(assignments, expected)
