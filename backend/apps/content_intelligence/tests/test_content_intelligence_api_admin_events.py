from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib import admin
from django.test import SimpleTestCase
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.content_intelligence.api.views import ContentImportJobViewSet
from apps.content_intelligence.api.serializers import ContentImportJobSerializer
from apps.content_intelligence.models import (
    ContentExtractionResult,
    ContentImportJob,
    ContentValidationFinding,
    ParsedConceptCandidate,
    ParsedDocument,
    ParsedSection,
    ParserPipelineRun,
)
from apps.content_intelligence.infrastructure.events.subscribers import LearningResourceUploadedSubscriber, StorageObjectReadySubscriber
from apps.core.events import default_event_registry
from apps.users.domain.models import User


class ContentIntelligenceApiAdminEventTests(SimpleTestCase):
    def test_ready_for_review_projection_is_non_failure_and_non_retryable(self):
        proposal = SimpleNamespace(
            id="proposal-1",
            review_state="ready_for_review",
            decision="pending",
            population_state="not_ready",
            statistics={"section_count": 376, "concept_count": 166},
            confidence=0.728,
            validations=Mock(),
        )
        proposal.validations.filter.return_value.count.return_value = 4
        processing_job = SimpleNamespace(
            id="processing-1",
            status="ready_for_review",
            current_stage="validating",
            progress=98,
            active_attempt_number=1,
            cancellation_requested=False,
            failure={},
            completed_at="2026-07-15T11:08:47Z",
            academic_import_proposals=Mock(),
        )
        processing_job.academic_import_proposals.order_by.return_value.first.return_value = proposal
        import_job = SimpleNamespace(processing_job=processing_job, error_message="")
        serializer = ContentImportJobSerializer()

        self.assertEqual(serializer.get_status_detail(import_job), "review_required")
        self.assertEqual(serializer.get_processing_message(import_job), "Review is required before academic content can be published.")
        self.assertTrue(serializer.get_review_required(import_job))
        self.assertFalse(serializer.get_ready_for_teaching(import_job))
        self.assertIsNone(serializer.get_processing_failure(import_job))
        self.assertFalse(serializer.get_can_retry_processing(import_job))
        self.assertFalse(serializer.get_can_cancel_processing(import_job))
        self.assertEqual(
            serializer.get_proposal(import_job),
            {
                "id": "proposal-1",
                "status": "ready_for_review",
                "decision": "pending",
                "population_state": "not_ready",
                "proposed_section_count": 376,
                "proposed_concept_count": 166,
                "confidence": 0.728,
                "blocking_finding_count": 4,
            },
        )

    def test_api_uses_authentication_permissions(self):
        self.assertEqual(ContentImportJobViewSet.permission_classes, [IsAuthenticated])

    def test_api_exposes_expected_actions(self):
        self.assertTrue(hasattr(ContentImportJobViewSet, "outline"))
        self.assertTrue(hasattr(ContentImportJobViewSet, "findings"))
        self.assertTrue(hasattr(ContentImportJobViewSet, "retry"))
        self.assertTrue(hasattr(ContentImportJobViewSet, "destroy"))

    def test_api_create_uses_services(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/api/content-intelligence/import-jobs/",
            {"learning_resource": "00000000-0000-0000-0000-000000000001"},
            format="json",
        )
        force_authenticate(request, user=User(id="user-1", email="user@example.com"))
        fake_job = Mock(spec=ContentImportJob)
        fake_job.id = "job-1"

        with patch("apps.content_intelligence.api.views.get_object_or_404", return_value=SimpleNamespace(id="00000000-0000-0000-0000-000000000001")):
            with patch("apps.content_intelligence.api.views.ImportService") as import_service:
                with patch("apps.content_intelligence.api.views.ContentImportJobSerializer") as serializer_class:
                    import_service.return_value.create_import_job.return_value = fake_job
                    serializer_class.return_value.data = {"id": "job-1"}
                    response = ContentImportJobViewSet.as_view({"post": "create"})(request)

        self.assertEqual(response.status_code, 201)
        import_service.return_value.create_import_job.assert_called_once()

    def test_api_create_returns_service_payload_without_pipeline_coupling(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/api/content-intelligence/import-jobs/",
            {"learning_resource": "00000000-0000-0000-0000-000000000001"},
            format="json",
        )
        force_authenticate(request, user=User(id="user-1", email="user@example.com"))
        fake_job = Mock(spec=ContentImportJob)
        fake_job.id = "job-1"

        with patch("apps.content_intelligence.api.views.get_object_or_404", return_value=SimpleNamespace(id="00000000-0000-0000-0000-000000000001")):
            with patch("apps.content_intelligence.api.views.ImportService") as import_service:
                with patch("apps.content_intelligence.api.views.ContentImportJobSerializer") as serializer_class:
                    import_service.return_value.create_import_job.return_value = fake_job
                    serializer_class.return_value.data = {"id": "job-1", "processing_status": "QUEUED"}
                    response = ContentImportJobViewSet.as_view({"post": "create"})(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["processing_status"], "QUEUED")

    def test_admin_registration_exists(self):
        for model in [ContentImportJob, ParsedDocument, ParsedSection, ParsedConceptCandidate, ContentExtractionResult, ContentValidationFinding, ParserPipelineRun]:
            self.assertIn(model, admin.site._registry)

    def test_event_registry_contains_content_intelligence_events(self):
        expected = {
            "content_intelligence.import_started",
            "content_intelligence.extraction_completed",
            "content_intelligence.ocr_requested",
            "content_intelligence.ocr_completed",
            "content_intelligence.sections_detected",
            "content_intelligence.concepts_extracted",
            "content_intelligence.import_validated",
            "content_intelligence.academic_population_completed",
            "content_intelligence.import_completed",
            "content_intelligence.import_failed",
            "content_intelligence.deletion_requested",
            "content_intelligence.deleted",
            "content_intelligence.stored_file_deletion_failed",
            "retrieval.resource_retired",
            "storage.file_contents_deleted",
        }
        self.assertTrue(expected.issubset(set(default_event_registry._subscribers)))

    def test_api_destroy_uses_deletion_service(self):
        factory = APIRequestFactory()
        request = factory.delete("/api/content-intelligence/import-jobs/job-1/")
        force_authenticate(request, user=User(id="user-1", email="user@example.com"))
        fake_job = Mock(spec=ContentImportJob)
        fake_job.id = "job-1"

        with patch.object(ContentImportJobViewSet, "get_object", return_value=fake_job):
            with patch("apps.content_intelligence.api.views.ContentImportDeletionService") as deletion_service:
                response = ContentImportJobViewSet.as_view({"delete": "destroy"})(request, pk="job-1")

        self.assertEqual(response.status_code, 204)
        deletion_service.return_value.delete_import.assert_called_once_with(fake_job)

    def test_event_subscribers_are_callable(self):
        event = SimpleNamespace(event_name="storage.file_uploaded", payload={})
        self.assertIsNone(StorageObjectReadySubscriber()(event))
        self.assertIsNone(LearningResourceUploadedSubscriber()(event))
