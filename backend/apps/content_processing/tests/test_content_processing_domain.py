from django.test import SimpleTestCase

from apps.content_processing.domain.exceptions import ProcessingLifecycleError, StaleProcessingAttemptError
from apps.content_processing.domain.models import (
    ContentProcessingJob,
    JobStatus,
    ProcessingFailure,
    ProcessingFailureCode,
    ProcessingStage,
    RetryClassification,
)


class ContentProcessingJobDomainTests(SimpleTestCase):
    def test_job_progresses_through_valid_lifecycle(self):
        job = ContentProcessingJob(active_attempt_number=1)

        job.queue()
        job.begin_stage(ProcessingStage.INSPECTING, 1)
        job.complete_stage(ProcessingStage.INSPECTING, ProcessingStage.EXTRACTING, 1)

        self.assertEqual(job.current_stage, ProcessingStage.EXTRACTING)
        self.assertEqual(job.progress, ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.EXTRACTING])

    def test_invalid_transition_is_rejected(self):
        job = ContentProcessingJob(active_attempt_number=1)

        with self.assertRaises(ProcessingLifecycleError):
            job.begin_stage(ProcessingStage.EXTRACTING, 1)

    def test_progress_is_monotonic_within_attempt(self):
        job = ContentProcessingJob(active_attempt_number=1)
        job.queue()
        job.begin_stage(ProcessingStage.INSPECTING, 1)
        job.report_progress(18, 1)

        with self.assertRaises(ProcessingLifecycleError):
            job.report_progress(12, 1)

    def test_stale_attempt_is_rejected(self):
        job = ContentProcessingJob(active_attempt_number=2)

        with self.assertRaises(StaleProcessingAttemptError):
            job.begin_stage(ProcessingStage.INSPECTING, 1)

    def test_retry_resets_failed_job_to_queued(self):
        job = ContentProcessingJob(active_attempt_number=1)
        job.fail(
            ProcessingFailure(
                code=ProcessingFailureCode.PDF_PARSE_FAILED,
                stage=ProcessingStage.EXTRACTING,
                public_message="The PDF could not be processed.",
                retry_classification=RetryClassification.RETRYABLE_SAME_STAGE,
            ),
            1,
        )

        job.begin_retry(2, ProcessingStage.EXTRACTING)

        self.assertEqual(job.status, JobStatus.ACTIVE)
        self.assertEqual(job.current_stage, ProcessingStage.QUEUED)
        self.assertEqual(job.active_attempt_number, 2)
        self.assertEqual(job.failure, {})

    def test_ready_for_teaching_requires_review_ready_state(self):
        job = ContentProcessingJob(active_attempt_number=1)

        with self.assertRaises(ProcessingLifecycleError):
            job.grant_teaching_readiness("evaluation-1")

        job.mark_ready_for_review()
        job.grant_teaching_readiness("evaluation-1")

        self.assertEqual(job.status, JobStatus.READY_FOR_TEACHING)
        self.assertEqual(job.progress, 100)
