from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.content_processing.application.services import (
    CreateContentProcessingJobService,
    DiagnosticRecord,
    OrchestrateContentProcessingStageService,
    ProcessingStageExecutionResult,
    QueueContentProcessingJobService,
    RetryContentProcessingJobService,
)
from apps.content_processing.domain.exceptions import StaleProcessingAttemptError
from apps.content_processing.domain.models import (
    AttemptStatus,
    AttemptTrigger,
    ContentProcessingJob,
    JobStatus,
    ProcessingAttempt,
    ProcessingFailureCode,
    ProcessingStage,
)
from apps.users.domain.models import User


class ContentProcessingServiceTests(SimpleTestCase):
    def test_create_job_is_idempotent_for_existing_active_identity(self):
        repository = Mock()
        attempt_repository = Mock()
        existing = ContentProcessingJob(id="job-1", active_attempt_number=1)
        repository.find_active_by_identity.return_value = existing

        service = CreateContentProcessingJobService(
            job_repository=repository,
            attempt_repository=attempt_repository,
            event_publisher=Mock(),
        )

        result = service.create_or_resolve(resource=SimpleNamespace(id="resource-1"), stored_file=None)

        self.assertIs(result, existing)
        repository.save.assert_not_called()
        attempt_repository.append.assert_not_called()

    def test_queue_service_moves_job_to_queued_and_dispatches_first_stage(self):
        repository = Mock()
        attempt_repository = Mock()
        event_publisher = Mock()
        job = ContentProcessingJob(id="job-1", active_attempt_number=1)
        repository.save.side_effect = lambda current_job: current_job
        attempt_repository.get_active.return_value = ProcessingAttempt(
            id="attempt-1",
            job=job,
            attempt_number=1,
            trigger=AttemptTrigger.INITIAL_UPLOAD,
            correlation_id="corr-1",
        )

        service = QueueContentProcessingJobService(
            job_repository=repository,
            attempt_repository=attempt_repository,
            event_publisher=event_publisher,
        )

        with patch("apps.content_processing.application.services.transaction.on_commit") as on_commit:
            result = service.queue(job)

        self.assertIs(result, job)
        self.assertEqual(job.current_stage, ProcessingStage.QUEUED)
        on_commit.assert_called_once()
        self.assertTrue(event_publisher.publish.called)

    def test_retry_service_creates_new_attempt_and_requeues(self):
        repository = Mock()
        repository.save.side_effect = lambda current_job: current_job
        attempt_repository = Mock()
        attempt_repository.append.side_effect = lambda attempt: attempt
        event_publisher = Mock()
        audit_service = Mock()
        job = ContentProcessingJob(
            id="job-1",
            status=JobStatus.FAILED,
            current_stage=ProcessingStage.EXTRACTING,
            active_attempt_number=1,
            failure={
                "code": ProcessingFailureCode.PDF_PARSE_FAILED,
                "stage": ProcessingStage.EXTRACTING,
            },
        )

        service = RetryContentProcessingJobService(
            job_repository=repository,
            attempt_repository=attempt_repository,
            event_publisher=event_publisher,
            audit_service=audit_service,
        )

        with patch("apps.content_processing.application.services.QueueContentProcessingJobService") as queue_service_class:
            queue_service_class.return_value.queue.return_value = job
            result = service.retry(job, actor=User(id="user-1", email="user@example.com"))

        self.assertIs(result, job)
        self.assertEqual(job.status, JobStatus.ACTIVE)
        self.assertEqual(job.current_stage, ProcessingStage.QUEUED)
        self.assertEqual(job.active_attempt_number, 2)
        attempt_repository.append.assert_called_once()
        audit_service.record_action.assert_called_once()

    def test_orchestrator_rejects_stale_attempt_execution(self):
        job_repository = Mock()
        attempt_repository = Mock()
        stage_result_repository = Mock()
        stage_result_repository.get.return_value = None
        job_repository.get_for_update.return_value = ContentProcessingJob(id="job-1", active_attempt_number=2)
        attempt_repository.get_by_id.return_value = ProcessingAttempt(
            id="attempt-1",
            job=ContentProcessingJob(id="job-1", active_attempt_number=2),
            attempt_number=1,
            trigger=AttemptTrigger.INITIAL_UPLOAD,
        )

        service = OrchestrateContentProcessingStageService(
            job_repository=job_repository,
            attempt_repository=attempt_repository,
            diagnostic_repository=Mock(),
            stage_result_repository=stage_result_repository,
            event_publisher=Mock(),
            registry=Mock(),
        )

        atomic = Mock()
        atomic.return_value.__enter__ = Mock(return_value=None)
        atomic.return_value.__exit__ = Mock(return_value=False)

        with patch("apps.content_processing.application.services.transaction.atomic", atomic):
            with self.assertRaisesMessage(StaleProcessingAttemptError, "stale attempt"):
                service.execute("job-1", "attempt-1", ProcessingStage.INSPECTING)

    def test_orchestrator_persists_stage_result_and_advances(self):
        job = ContentProcessingJob(
            id="job-1",
            active_attempt_number=1,
            current_stage=ProcessingStage.QUEUED,
            progress=ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.QUEUED],
        )
        attempt = ProcessingAttempt(
            id="attempt-1",
            job=job,
            attempt_number=1,
            trigger=AttemptTrigger.INITIAL_UPLOAD,
        )
        job_repository = Mock()
        job_repository.get_for_update.return_value = job
        job_repository.save.side_effect = lambda current_job: current_job
        attempt_repository = Mock()
        attempt_repository.get_by_id.return_value = attempt
        attempt_repository.save.side_effect = lambda current_attempt: current_attempt
        diagnostic_repository = Mock()
        stage_result_repository = Mock()
        stage_result_repository.get.return_value = None
        stage_result_repository.save.side_effect = lambda result: result
        registry = Mock()
        registry.get.return_value.execute.return_value = ProcessingStageExecutionResult(
            completed_stage=ProcessingStage.INSPECTING,
            next_stage=ProcessingStage.EXTRACTING,
            progress=25,
            diagnostics=(
                DiagnosticRecord(
                    stage=ProcessingStage.INSPECTING,
                    severity="info",
                    code="inspection_complete",
                    public_message="Inspection complete.",
                ),
            ),
        )

        service = OrchestrateContentProcessingStageService(
            job_repository=job_repository,
            attempt_repository=attempt_repository,
            diagnostic_repository=diagnostic_repository,
            stage_result_repository=stage_result_repository,
            event_publisher=Mock(),
            registry=registry,
        )

        atomic = Mock()
        atomic.return_value.__enter__ = Mock(return_value=None)
        atomic.return_value.__exit__ = Mock(return_value=False)

        with patch("apps.content_processing.application.services.transaction.atomic", atomic):
            with patch("apps.content_processing.application.services.transaction.on_commit") as on_commit:
                result = service.execute("job-1", "attempt-1", ProcessingStage.INSPECTING, "corr-1")

        self.assertIs(result, job)
        self.assertEqual(job.current_stage, ProcessingStage.EXTRACTING)
        self.assertEqual(attempt.status, AttemptStatus.PENDING)
        stage_result_repository.save.assert_called_once()
        on_commit.assert_called_once()
