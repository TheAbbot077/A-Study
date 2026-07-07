from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.academic.domain.models import LearningResource, ResourceIngestionJob
from apps.academic.services.resource_ingestion_service import ResourceIngestionService


class DummyLearningResource:
    id = "resource-1"


class ResourceIngestionServiceTests(SimpleTestCase):
    def test_create_job_publishes_event(self):
        publisher = Mock()
        service = ResourceIngestionService(event_publisher=publisher)
        learning_resource = DummyLearningResource()

        with patch("apps.academic.services.resource_ingestion_service.ResourceIngestionJob.objects") as job_objects:
            fake_job = Mock(spec=ResourceIngestionJob)
            fake_job.id = "job-1"
            fake_job.learning_resource_id = learning_resource.id
            job_objects.create.return_value = fake_job

            job = service.create_job(learning_resource, source_type=ResourceIngestionJob.SourceType.UPLOAD)

        self.assertIs(job, fake_job)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.resource_ingestion_job_created")

    def test_lifecycle_methods_publish_events(self):
        publisher = Mock()
        service = ResourceIngestionService(event_publisher=publisher)
        job = Mock(spec=ResourceIngestionJob)
        job.id = "job-1"
        job.learning_resource_id = "resource-1"
        job.status = ResourceIngestionJob.Status.PENDING
        job.started_at = None
        job.completed_at = None
        job.error_message = ""

        started = service.start_job(job)
        completed = service.complete_job(job)
        failed = service.fail_job(job, "parse error")
        cancelled = service.cancel_job(job)

        self.assertIs(started, job)
        self.assertIs(completed, job)
        self.assertIs(failed, job)
        self.assertIs(cancelled, job)
        self.assertEqual(publisher.publish.call_count, 4)

    def test_list_and_get_jobs(self):
        service = ResourceIngestionService(event_publisher=Mock())
        learning_resource = DummyLearningResource()
        expected_jobs = [Mock()]

        with patch("apps.academic.services.resource_ingestion_service.ResourceIngestionJob.objects") as job_objects:
            job_objects.all.return_value.order_by.return_value = expected_jobs
            job_objects.filter.return_value.order_by.return_value = expected_jobs
            job_objects.get.return_value = expected_jobs[0]

            listed = service.list_jobs()
            listed_for_resource = service.list_jobs_for_resource(learning_resource)
            fetched = service.get_job(learning_resource, "job-1")

        self.assertEqual(listed, expected_jobs)
        self.assertEqual(listed_for_resource, expected_jobs)
        self.assertIs(fetched, expected_jobs[0])

    def test_model_choices_are_available(self):
        self.assertEqual(ResourceIngestionJob.Status.values, ["pending", "processing", "completed", "failed", "cancelled"])
        self.assertEqual(ResourceIngestionJob.SourceType.values, ["manual", "upload", "import", "system"])
