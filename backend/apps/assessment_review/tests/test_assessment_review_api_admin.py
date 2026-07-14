from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.test import SimpleTestCase
from rest_framework import serializers
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.assessment_review.api.serializers import ReviewerAssignmentSerializer
from apps.assessment_review.api.views import AssessmentReviewAnalyticsViewSet, AssessmentReviewViewSet, QuestionReviewViewSet
from apps.assessment_review.domain.models import AssessmentReview, DifficultyCalibration, QuestionReview, QualityFinding, ReviewDecision, ReviewerAssignment
from apps.assessment_review.infrastructure.events.subscribers import (
    AssessmentEvaluatedReviewSubscriber,
    AssessmentPublishedReviewSubscriber,
    EvidenceIntegratedReviewSubscriber,
    QuestionAuthoredReviewSubscriber,
)
from apps.users.domain.models import User


class AssessmentReviewApiAdminTests(SimpleTestCase):
    def test_assessment_review_pending_endpoint_uses_service(self):
        factory = APIRequestFactory()
        request = factory.get("/api/assessment-review/assessment-reviews/pending/")
        force_authenticate(request, user=User(id="user-1", email="reviewer@example.com"))

        with patch("apps.assessment_review.api.views.AssessmentReviewService") as service_class:
            service_class.return_value.list_pending_reviews.return_value = []
            response = AssessmentReviewViewSet.as_view({"get": "pending"})(request)

        self.assertEqual(response.status_code, 200)
        service_class.return_value.list_pending_reviews.assert_called_once()

    def test_analytics_endpoint_returns_platform_metrics(self):
        factory = APIRequestFactory()
        request = factory.get("/api/assessment-review/analytics/")
        force_authenticate(request, user=User(id="user-1", email="reviewer@example.com"))

        with patch("apps.assessment_review.api.views.AssessmentAnalyticsService") as service_class:
            service_class.return_value.platform_metrics.return_value = {"review_backlog": 2}
            response = AssessmentReviewAnalyticsViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["review_backlog"], 2)

    def test_invalid_question_review_transition_returns_400(self):
        factory = APIRequestFactory()
        request = factory.post("/api/assessment-review/question-reviews/question-1/start/")
        force_authenticate(request, user=User(id="user-1", email="reviewer@example.com"))

        with patch("apps.assessment_review.api.views.QuestionReviewService") as service_class:
            with patch.object(QuestionReviewViewSet, "get_object", return_value=QuestionReview(status="approved")):
                service_class.return_value.start_review.side_effect = ValueError("Cannot transition review from approved to in_review.")
                response = QuestionReviewViewSet.as_view({"post": "start"})(request, pk="question-1")

        self.assertEqual(response.status_code, 400)

    def test_admin_registration_exists(self):
        for model in [AssessmentReview, QuestionReview, DifficultyCalibration, QualityFinding, ReviewDecision, ReviewerAssignment]:
            self.assertIn(model, admin.site._registry)

    def test_reviewer_assignment_serializer_requires_single_target(self):
        with self.assertRaises(serializers.ValidationError):
            ReviewerAssignmentSerializer().validate({})

    def test_event_subscribers_are_callable(self):
        event = SimpleNamespace(event_name="assessment.attempt_evaluated", payload={})
        for subscriber in [
            QuestionAuthoredReviewSubscriber(),
            AssessmentEvaluatedReviewSubscriber(),
            EvidenceIntegratedReviewSubscriber(),
            AssessmentPublishedReviewSubscriber(),
        ]:
            self.assertIsNone(subscriber(event))
