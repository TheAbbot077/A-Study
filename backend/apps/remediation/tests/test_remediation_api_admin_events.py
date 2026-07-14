from unittest.mock import patch

from django.contrib import admin
from django.test import SimpleTestCase
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.core.events import default_event_registry
from apps.remediation.api.views import RemediationPlanViewSet
from apps.remediation.domain.models import (
    RemediationActivity,
    RemediationAttempt,
    RemediationOutcome,
    RemediationPlan,
    RemediationRecommendation,
)
from apps.users.domain.models import User


class RemediationApiAdminEventTests(SimpleTestCase):
    def test_api_uses_authentication_permissions(self):
        self.assertEqual(RemediationPlanViewSet.permission_classes, [IsAuthenticated])

    def test_api_exposes_expected_actions(self):
        self.assertTrue(hasattr(RemediationPlanViewSet, "start"))
        self.assertTrue(hasattr(RemediationPlanViewSet, "complete"))
        self.assertTrue(hasattr(RemediationPlanViewSet, "cancel"))
        self.assertTrue(hasattr(RemediationPlanViewSet, "history"))

    def test_invalid_remediation_transition_returns_400(self):
        factory = APIRequestFactory()
        request = factory.post("/api/remediation/plans/plan-1/start/")
        force_authenticate(request, user=User(id="user-1", email="user@example.com"))

        with patch("apps.remediation.api.views.RemediationExecutionService") as service_class:
            with patch.object(RemediationPlanViewSet, "get_object", return_value=RemediationPlan(status="closed")):
                service_class.return_value.start_remediation.side_effect = ValueError("Cannot start remediation plan from closed.")
                response = RemediationPlanViewSet.as_view({"post": "start"})(request, pk="plan-1")

        self.assertEqual(response.status_code, 400)

    def test_admin_registration(self):
        for model in [RemediationPlan, RemediationRecommendation, RemediationActivity, RemediationAttempt, RemediationOutcome]:
            self.assertIn(model, admin.site._registry)

    def test_admin_filters_and_search(self):
        model_admin = admin.site._registry[RemediationPlan]

        self.assertIn("status", model_admin.list_filter)
        self.assertIn("content_concept__title", model_admin.search_fields)

    def test_remediation_events_registered(self):
        expected = {
            "remediation.planned",
            "remediation.started",
            "remediation.completed",
            "remediation.escalated",
            "remediation.cancelled",
            "remediation.closed",
        }

        self.assertTrue(expected.issubset(set(default_event_registry._subscribers)))

    def test_regression_assessment_evidence_mastery_events_unchanged(self):
        expected_existing_events = {
            "assessment.evaluation_integrated_as_evidence",
            "assessment.mastery_profile_updated",
            "assessment.response_evaluated",
        }

        self.assertTrue(expected_existing_events.issubset(set(default_event_registry._subscribers)))
