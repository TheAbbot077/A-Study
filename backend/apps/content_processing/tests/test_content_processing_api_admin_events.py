from django.contrib import admin
from django.test import SimpleTestCase
from rest_framework.permissions import IsAuthenticated
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.content_processing.api.views import ContentProcessingJobViewSet
from apps.content_processing.models import (
    ContentProcessingJob,
    ProcessingAttempt,
    ProcessingDiagnostic,
    ProcessingStageResult,
)
from apps.core.events import default_event_registry


class ContentProcessingApiAdminEventTests(SimpleTestCase):
    def test_api_uses_authentication_permissions(self):
        self.assertEqual(ContentProcessingJobViewSet.permission_classes, [IsAuthenticated])

    def test_api_exposes_expected_actions(self):
        self.assertTrue(hasattr(ContentProcessingJobViewSet, "attempts"))
        self.assertTrue(hasattr(ContentProcessingJobViewSet, "diagnostics"))
        self.assertTrue(hasattr(ContentProcessingJobViewSet, "retry"))
        self.assertTrue(hasattr(ContentProcessingJobViewSet, "cancel"))

    def test_job_list_can_resolve_canonical_processing_by_resource(self):
        view = ContentProcessingJobViewSet()
        view.request = SimpleNamespace(
            user=SimpleNamespace(id="user-1"),
            query_params={"resource": "resource-1"},
        )
        scoped_queryset = MagicMock()
        resource_queryset = MagicMock()
        with (
            patch("apps.content_processing.api.views.ContentProcessingJob.objects") as jobs,
            patch("apps.content_processing.api.views.InstitutionMembership.objects") as memberships,
        ):
            jobs.select_related.return_value.order_by.return_value.filter.return_value = scoped_queryset
            scoped_queryset.filter.return_value = resource_queryset
            memberships.filter.return_value.values_list.return_value = ["institution-1"]
            result = view.get_queryset()
        scoped_queryset.filter.assert_called_once_with(resource_id="resource-1")
        self.assertIs(result, resource_queryset)

    def test_admin_registration_exists(self):
        for model in [ContentProcessingJob, ProcessingAttempt, ProcessingDiagnostic, ProcessingStageResult]:
            self.assertIn(model, admin.site._registry)

    def test_event_registry_contains_content_processing_events(self):
        expected = {
            "content_processing.job_created",
            "content_processing.job_queued",
            "content_processing.attempt_started",
            "content_processing.stage_started",
            "content_processing.stage_progressed",
            "content_processing.stage_completed",
            "content_processing.diagnostic_recorded",
            "content_processing.job_failed",
            "content_processing.retry_requested",
            "content_processing.job_cancel_requested",
            "content_processing.job_cancelled",
            "content_processing.ready_for_review",
            "content_processing.ready_for_teaching",
            "content_processing.job_deleted",
        }
        self.assertTrue(expected.issubset(set(default_event_registry._subscribers)))
