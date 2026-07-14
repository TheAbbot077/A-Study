from django.contrib import admin
from django.test import SimpleTestCase
from rest_framework.permissions import IsAuthenticated

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
