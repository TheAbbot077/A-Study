from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional, Protocol

from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.content_processing.domain.models import (
    AttemptStatus,
    AttemptTrigger,
    ContentProcessingJob,
    DiagnosticSeverity,
    JobStatus,
    ProcessingAttempt,
    ProcessingDiagnostic,
    ProcessingFailure,
    ProcessingFailureCode,
    ProcessingStage,
    ProcessingStageResult,
    RetryClassification,
)
from apps.content_processing.domain.exceptions import (
    ProcessingLifecycleError,
    StaleProcessingAttemptError,
)
from apps.content_processing.domain.repositories import (
    ContentProcessingJobRepository,
    ProcessingAttemptRepository,
    ProcessingDiagnosticRepository,
    ProcessingStageResultRepository,
)
from apps.content_processing.infrastructure.persistence import (
    DjangoContentProcessingJobRepository,
    DjangoProcessingAttemptRepository,
    DjangoProcessingDiagnosticRepository,
    DjangoProcessingStageResultRepository,
)
from apps.core.events import BusinessEvent, EventPublisher


PROCESSING_PIPELINE_VERSION = ContentProcessingJob.PIPELINE_VERSION


STAGE_LABELS = {
    ProcessingStage.CREATED: "Uploaded",
    ProcessingStage.QUEUED: "Queued",
    ProcessingStage.INSPECTING: "Inspecting",
    ProcessingStage.EXTRACTING: "Extracting",
    ProcessingStage.STRUCTURING: "Organizing chapters and sections",
    ProcessingStage.SEGMENTING: "Segmenting",
    ProcessingStage.VALIDATING: "Validating",
    ProcessingStage.POPULATING: "Preparing academic content",
    ProcessingStage.INDEXING: "Indexing",
    JobStatus.READY_FOR_REVIEW: "Ready for review",
    JobStatus.READY_FOR_TEACHING: "Ready for teaching",
    JobStatus.FAILED: "Content processing failed",
    JobStatus.CANCELLED: "Processing cancelled",
    JobStatus.DELETED: "Deleted",
}


@dataclass(frozen=True)
class ProcessingStageContext:
    job_id: str
    attempt_id: str
    resource_id: str | None
    stored_file_id: str | None
    pipeline_version: str
    expected_stage: str
    correlation_id: str


@dataclass(frozen=True)
class DiagnosticRecord:
    stage: str
    severity: str
    code: str
    public_message: str
    internal_message: str = ""
    details: dict[str, object] = field(default_factory=dict)
    source_component: str = ""


@dataclass(frozen=True)
class ProcessingStageExecutionResult:
    completed_stage: str
    next_stage: str | None
    progress: int
    diagnostics: tuple[DiagnosticRecord, ...] = ()
    output_references: dict[str, object] = field(default_factory=dict)
    checksum: str = ""
    terminal_status: str | None = None


class ProcessingStageProcessor(Protocol):
    def supports(self, stage: str) -> bool: ...
    def execute(self, context: ProcessingStageContext) -> ProcessingStageExecutionResult: ...


class RetryPolicy:
    MAX_ATTEMPTS = 3

    def classify(self, failure_code: str) -> str:
        if failure_code in {
            ProcessingFailureCode.STORAGE_READ_FAILED,
            ProcessingFailureCode.PDF_PARSE_FAILED,
            ProcessingFailureCode.DOCX_PARSE_FAILED,
            ProcessingFailureCode.ACADEMIC_IMPORT_FAILED,
            ProcessingFailureCode.INDEXING_FAILED,
            ProcessingFailureCode.CHUNK_BUILD_FAILED,
            ProcessingFailureCode.EMBEDDING_FAILED,
            ProcessingFailureCode.INDEX_FAILED,
            ProcessingFailureCode.PROVIDER_UNAVAILABLE,
            ProcessingFailureCode.UNEXPECTED_PROCESSING_FAILURE,
        }:
            return RetryClassification.RETRYABLE_SAME_STAGE
        if failure_code == ProcessingFailureCode.OCR_UNAVAILABLE:
            return RetryClassification.REQUIRES_OPERATOR_ACTION
        if failure_code in {ProcessingFailureCode.UNSUPPORTED_FORMAT, ProcessingFailureCode.NO_ACADEMIC_CONTENT, ProcessingFailureCode.VALIDATION_FAILED}:
            return RetryClassification.NON_RETRYABLE
        return RetryClassification.REQUIRES_OPERATOR_ACTION

    def can_retry(self, job: ContentProcessingJob) -> bool:
        if job.status not in {JobStatus.FAILED, JobStatus.CANCELLED}:
            return False
        if job.active_attempt_number >= self.MAX_ATTEMPTS:
            return False
        failure_code = (job.failure or {}).get("code", "")
        return self.classify(failure_code) != RetryClassification.NON_RETRYABLE

    def restart_stage(self, job: ContentProcessingJob) -> str:
        failure_code = (job.failure or {}).get("code", "")
        if self.classify(failure_code) == RetryClassification.RETRYABLE_FROM_PRIOR_STAGE:
            return ProcessingStage.INSPECTING
        failed_stage = (job.failure or {}).get("stage")
        return failed_stage or ProcessingStage.INSPECTING


class StageProcessorRegistry:
    def __init__(self, processors: list[ProcessingStageProcessor]) -> None:
        self.processors = processors

    def get(self, stage: str) -> ProcessingStageProcessor:
        for processor in self.processors:
            if processor.supports(stage):
                return processor
        raise ValueError(f"No processor is registered for stage {stage}.")


class LegacyParserCompatibilityProcessor:
    def __init__(self, stage: str) -> None:
        self.stage = stage

    def supports(self, stage: str) -> bool:
        return stage == self.stage

    def execute(self, context: ProcessingStageContext) -> ProcessingStageExecutionResult:
        if self.stage == ProcessingStage.INSPECTING:
            return ProcessingStageExecutionResult(
                completed_stage=self.stage,
                next_stage=ProcessingStage.EXTRACTING,
                progress=ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.INSPECTING],
                diagnostics=(
                    DiagnosticRecord(
                        stage=self.stage,
                        severity=DiagnosticSeverity.INFO,
                        code="inspection_started",
                        public_message="File inspection completed.",
                        source_component="legacy_parser_adapter",
                    ),
                ),
            )
        if self.stage == ProcessingStage.EXTRACTING:
            return ProcessingStageExecutionResult(
                completed_stage=self.stage,
                next_stage=ProcessingStage.STRUCTURING,
                progress=ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.EXTRACTING],
            )
        if self.stage == ProcessingStage.STRUCTURING:
            return ProcessingStageExecutionResult(
                completed_stage=self.stage,
                next_stage=ProcessingStage.SEGMENTING,
                progress=ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.STRUCTURING],
            )
        if self.stage == ProcessingStage.SEGMENTING:
            return ProcessingStageExecutionResult(
                completed_stage=self.stage,
                next_stage=ProcessingStage.VALIDATING,
                progress=ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.SEGMENTING],
            )
        if self.stage == ProcessingStage.VALIDATING:
            return ProcessingStageExecutionResult(
                completed_stage=self.stage,
                next_stage=ProcessingStage.POPULATING,
                progress=ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.VALIDATING],
            )
        if self.stage == ProcessingStage.POPULATING:
            from apps.content_intelligence.application.pipeline_service import PipelineService
            from apps.content_processing.application.document_services import LegacyBlockExtractionService
            from apps.content_processing.application.structure_services import LegacyHierarchySectionProjectionService
            from apps.content_processing.models import ContentProcessingJob as ORMContentProcessingJob

            job = ORMContentProcessingJob.objects.select_related("legacy_import_job").get(id=context.job_id)
            if job.legacy_import_job is None:
                raise RuntimeError("The legacy content import job is missing.")
            extraction = job.document_extractions.filter(attempt__attempt_number=job.active_attempt_number).order_by("-created_at").first()
            hierarchy = job.document_hierarchies.filter(attempt__attempt_number=job.active_attempt_number).order_by("-created_at").first()
            pipeline = PipelineService(
                extraction_service=LegacyBlockExtractionService(extraction),
                section_detection_service=LegacyHierarchySectionProjectionService(hierarchy) if hierarchy else None,
            ) if extraction else PipelineService()
            pipeline.run_pipeline(job.legacy_import_job)
            output_references = {
                "legacy_import_job_id": str(job.legacy_import_job_id),
                "learning_resource_id": str(job.resource_id) if job.resource_id else None,
            }
            return ProcessingStageExecutionResult(
                completed_stage=self.stage,
                next_stage=ProcessingStage.INDEXING,
                progress=ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.POPULATING],
                output_references=output_references,
            )
        if self.stage == ProcessingStage.INDEXING:
            return ProcessingStageExecutionResult(
                completed_stage=self.stage,
                next_stage=None,
                progress=ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.INDEXING],
            )
        raise ValueError(f"Unsupported compatibility stage: {self.stage}")


def build_default_registry() -> StageProcessorRegistry:
    from apps.content_processing.application.stage_processors import BuildSemanticSegmentsProcessor, ExtractSourceDocumentProcessor, GenerateAcademicImportProposalProcessor, IndexAcademicPopulationProcessor, InspectSourceDocumentProcessor, PopulateAcademicPlatformProcessor, ReconstructDocumentHierarchyProcessor
    return StageProcessorRegistry(
        processors=[
            InspectSourceDocumentProcessor(),
            ExtractSourceDocumentProcessor(),
            ReconstructDocumentHierarchyProcessor(),
            BuildSemanticSegmentsProcessor(),
            GenerateAcademicImportProposalProcessor(),
            PopulateAcademicPlatformProcessor(),
            IndexAcademicPopulationProcessor(),
        ]
    )


class LegacyImportProjectionService:
    def project(self, job: ContentProcessingJob) -> None:
        legacy_job = job.legacy_import_job
        if legacy_job is None:
            return
        if job.status == JobStatus.FAILED:
            legacy_job.status = legacy_job.Status.FAILED
            legacy_job.error_message = (job.failure or {}).get("public_message") or legacy_job.error_message
        elif job.status == JobStatus.CANCELLED:
            legacy_job.status = legacy_job.Status.CANCELLED
            legacy_job.error_message = (job.failure or {}).get("public_message", "")
        elif job.status == JobStatus.DELETED:
            return
        elif job.status == JobStatus.READY_FOR_TEACHING:
            legacy_job.status = legacy_job.Status.COMPLETED
            legacy_job.error_message = ""
        elif job.status == JobStatus.READY_FOR_REVIEW:
            legacy_job.status = legacy_job.Status.PROCESSING
            legacy_job.error_message = "Review is required before academic content can be published."
        elif job.current_stage in {ProcessingStage.CREATED, ProcessingStage.QUEUED}:
            legacy_job.status = legacy_job.Status.PENDING
        else:
            legacy_job.status = legacy_job.Status.PROCESSING
        legacy_job.save(update_fields=["status", "error_message", "updated_at"])


class CreateContentProcessingJobService:
    def __init__(
        self,
        job_repository: Optional[ContentProcessingJobRepository] = None,
        attempt_repository: Optional[ProcessingAttemptRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.job_repository = job_repository or DjangoContentProcessingJobRepository()
        self.attempt_repository = attempt_repository or DjangoProcessingAttemptRepository()
        self.event_publisher = event_publisher or EventPublisher()

    def create_or_resolve(self, *, resource, stored_file=None, legacy_import_job=None, requested_by=None) -> ContentProcessingJob:
        existing = self.job_repository.find_active_by_identity(str(resource.id), str(getattr(stored_file, "id", None)) if stored_file else None, PROCESSING_PIPELINE_VERSION)
        if existing is not None:
            return existing
        job = ContentProcessingJob(
            resource=resource,
            stored_file=stored_file,
            legacy_import_job=legacy_import_job,
            pipeline_version=PROCESSING_PIPELINE_VERSION,
            status=JobStatus.ACTIVE,
            current_stage=ProcessingStage.CREATED,
            progress=ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.CREATED],
            active_attempt_number=1,
        )
        job = self.job_repository.save(job)
        attempt = ProcessingAttempt(
            job=job,
            attempt_number=1,
            trigger=AttemptTrigger.INITIAL_UPLOAD,
            restart_stage=ProcessingStage.INSPECTING,
            status=AttemptStatus.PENDING,
            correlation_id=str(uuid.uuid4()),
            initiated_by_actor=requested_by,
        )
        self.attempt_repository.append(attempt)
        self.event_publisher.publish(
            BusinessEvent.create(
                "content_processing.job_created",
                payload={
                    "job_id": str(job.id),
                    "attempt_id": str(attempt.id),
                    "resource_id": str(job.resource_id) if job.resource_id else None,
                    "stored_file_id": str(job.stored_file_id) if job.stored_file_id else None,
                    "pipeline_version": job.pipeline_version,
                    "stage": job.current_stage,
                },
            )
        )
        return job


class QueueContentProcessingJobService:
    def __init__(
        self,
        job_repository: Optional[ContentProcessingJobRepository] = None,
        attempt_repository: Optional[ProcessingAttemptRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.job_repository = job_repository or DjangoContentProcessingJobRepository()
        self.attempt_repository = attempt_repository or DjangoProcessingAttemptRepository()
        self.event_publisher = event_publisher or EventPublisher()

    def queue(self, job: ContentProcessingJob) -> ContentProcessingJob:
        active_attempt = self.attempt_repository.get_active(str(job.id))
        if active_attempt is None:
            raise ProcessingLifecycleError("A queued processing job requires an active attempt.")
        job.queue()
        job = self.job_repository.save(job)
        LegacyImportProjectionService().project(job)
        self.event_publisher.publish(
            BusinessEvent.create(
                "content_processing.job_queued",
                payload={
                    "job_id": str(job.id),
                    "attempt_id": str(active_attempt.id),
                    "resource_id": str(job.resource_id) if job.resource_id else None,
                    "stored_file_id": str(job.stored_file_id) if job.stored_file_id else None,
                    "pipeline_version": job.pipeline_version,
                    "stage": job.current_stage,
                    "progress": job.progress,
                },
            )
        )
        from apps.content_processing.infrastructure.celery.tasks import process_content_processing_stage_task

        transaction.on_commit(
            lambda: process_content_processing_stage_task.delay(
                str(job.id),
                str(active_attempt.id),
                ProcessingStage.INSPECTING,
                active_attempt.correlation_id,
            )
        )
        return job


class RecordProcessingDiagnosticService:
    def __init__(
        self,
        diagnostic_repository: Optional[ProcessingDiagnosticRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.diagnostic_repository = diagnostic_repository or DjangoProcessingDiagnosticRepository()
        self.event_publisher = event_publisher or EventPublisher()

    def record(self, job: ContentProcessingJob, attempt: ProcessingAttempt, diagnostic: DiagnosticRecord) -> ProcessingDiagnostic:
        saved = self.diagnostic_repository.append(
            ProcessingDiagnostic(
                job=job,
                attempt=attempt,
                stage=diagnostic.stage,
                severity=diagnostic.severity,
                code=diagnostic.code,
                public_message=diagnostic.public_message,
                internal_message=diagnostic.internal_message,
                details=diagnostic.details,
                source_component=diagnostic.source_component,
            )
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "content_processing.diagnostic_recorded",
                payload={
                    "job_id": str(job.id),
                    "attempt_id": str(attempt.id),
                    "stage": diagnostic.stage,
                    "severity": diagnostic.severity,
                    "code": diagnostic.code,
                },
            )
        )
        return saved


class FailContentProcessingJobService:
    def __init__(
        self,
        job_repository: Optional[ContentProcessingJobRepository] = None,
        attempt_repository: Optional[ProcessingAttemptRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.job_repository = job_repository or DjangoContentProcessingJobRepository()
        self.attempt_repository = attempt_repository or DjangoProcessingAttemptRepository()
        self.event_publisher = event_publisher or EventPublisher()

    def fail(self, job: ContentProcessingJob, attempt: ProcessingAttempt, failure: ProcessingFailure) -> ContentProcessingJob:
        attempt.status = AttemptStatus.FAILED
        attempt.failure = failure.to_dict()
        attempt.completed_at = timezone.now()
        self.attempt_repository.save(attempt)
        job.fail(failure, attempt.attempt_number)
        job = self.job_repository.save(job)
        LegacyImportProjectionService().project(job)
        self.event_publisher.publish(
            BusinessEvent.create(
                "content_processing.job_failed",
                payload={
                    "job_id": str(job.id),
                    "attempt_id": str(attempt.id),
                    "resource_id": str(job.resource_id) if job.resource_id else None,
                    "stage": failure.stage,
                    "failure_code": failure.code,
                },
            )
        )
        return job


class RetryContentProcessingJobService:
    def __init__(
        self,
        job_repository: Optional[ContentProcessingJobRepository] = None,
        attempt_repository: Optional[ProcessingAttemptRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
        audit_service: Optional[AuditService] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        self.job_repository = job_repository or DjangoContentProcessingJobRepository()
        self.attempt_repository = attempt_repository or DjangoProcessingAttemptRepository()
        self.event_publisher = event_publisher or EventPublisher()
        self.audit_service = audit_service or AuditService(event_publisher=self.event_publisher)
        self.retry_policy = retry_policy or RetryPolicy()

    def retry(self, job: ContentProcessingJob, actor=None) -> ContentProcessingJob:
        if not self.retry_policy.can_retry(job):
            raise ProcessingLifecycleError("This processing job cannot be retried.")
        next_attempt_number = job.active_attempt_number + 1
        restart_stage = self.retry_policy.restart_stage(job)
        attempt = self.attempt_repository.append(
            ProcessingAttempt(
                job=job,
                attempt_number=next_attempt_number,
                trigger=AttemptTrigger.MANUAL_RETRY,
                restart_stage=restart_stage,
                status=AttemptStatus.PENDING,
                correlation_id=str(uuid.uuid4()),
                initiated_by_actor=actor,
            )
        )
        job.begin_retry(next_attempt_number, restart_stage)
        job = self.job_repository.save(job)
        LegacyImportProjectionService().project(job)
        self.audit_service.record_action(
            actor=actor,
            action="content_processing.retry_requested",
            target_type="content_processing_job",
            target_id=str(job.id),
            metadata={"attempt_id": str(attempt.id), "restart_stage": restart_stage},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "content_processing.retry_requested",
                payload={"job_id": str(job.id), "attempt_id": str(attempt.id), "stage": restart_stage},
            )
        )
        return QueueContentProcessingJobService(
            job_repository=self.job_repository,
            attempt_repository=self.attempt_repository,
            event_publisher=self.event_publisher,
        ).queue(job)


class CancelContentProcessingJobService:
    def __init__(
        self,
        job_repository: Optional[ContentProcessingJobRepository] = None,
        attempt_repository: Optional[ProcessingAttemptRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        self.job_repository = job_repository or DjangoContentProcessingJobRepository()
        self.attempt_repository = attempt_repository or DjangoProcessingAttemptRepository()
        self.event_publisher = event_publisher or EventPublisher()
        self.audit_service = audit_service or AuditService(event_publisher=self.event_publisher)

    def cancel(self, job: ContentProcessingJob, actor=None) -> ContentProcessingJob:
        active_attempt = self.attempt_repository.get_active(str(job.id))
        job.request_cancellation()
        if job.current_stage in {ProcessingStage.CREATED, ProcessingStage.QUEUED}:
            job.cancel()
            if active_attempt is not None:
                active_attempt.status = AttemptStatus.CANCELLED
                active_attempt.completed_at = timezone.now()
                self.attempt_repository.save(active_attempt)
        job = self.job_repository.save(job)
        LegacyImportProjectionService().project(job)
        self.audit_service.record_action(
            actor=actor,
            action="content_processing.cancel_requested",
            target_type="content_processing_job",
            target_id=str(job.id),
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "content_processing.job_cancel_requested",
                payload={"job_id": str(job.id), "attempt_id": str(active_attempt.id) if active_attempt else None},
            )
        )
        if job.status == JobStatus.CANCELLED:
            self.event_publisher.publish(
                BusinessEvent.create(
                    "content_processing.job_cancelled",
                    payload={"job_id": str(job.id), "attempt_id": str(active_attempt.id) if active_attempt else None},
                )
            )
        return job


class DeleteContentProcessingJobService:
    def __init__(
        self,
        job_repository: Optional[ContentProcessingJobRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        self.job_repository = job_repository or DjangoContentProcessingJobRepository()
        self.event_publisher = event_publisher or EventPublisher()
        self.audit_service = audit_service or AuditService(event_publisher=self.event_publisher)

    def mark_deleted(self, job: ContentProcessingJob, actor=None) -> ContentProcessingJob:
        if job.status != JobStatus.DELETED:
            job.mark_deleted()
            job = self.job_repository.save(job)
            self.audit_service.record_action(
                actor=actor,
                action="content_processing.deleted",
                target_type="content_processing_job",
                target_id=str(job.id),
            )
            self.event_publisher.publish(
                BusinessEvent.create(
                    "content_processing.job_deleted",
                    payload={"job_id": str(job.id), "resource_id": str(job.resource_id) if job.resource_id else None},
                )
            )
        return job


class MarkContentReadyForReviewService:
    def __init__(self, job_repository: Optional[ContentProcessingJobRepository] = None, event_publisher: Optional[EventPublisher] = None) -> None:
        self.job_repository = job_repository or DjangoContentProcessingJobRepository()
        self.event_publisher = event_publisher or EventPublisher()

    def mark(self, job: ContentProcessingJob) -> ContentProcessingJob:
        job.mark_ready_for_review()
        job = self.job_repository.save(job)
        self.event_publisher.publish(BusinessEvent.create("content_processing.ready_for_review", payload={"job_id": str(job.id)}))
        LegacyImportProjectionService().project(job)
        return job


class MarkContentReadyForTeachingService:
    def __init__(self, job_repository: Optional[ContentProcessingJobRepository] = None, event_publisher: Optional[EventPublisher] = None) -> None:
        self.job_repository = job_repository or DjangoContentProcessingJobRepository()
        self.event_publisher = event_publisher or EventPublisher()

    def mark(self, job: ContentProcessingJob) -> ContentProcessingJob:
        raise ProcessingLifecycleError(
            "Teaching readiness may only be granted by EvaluateTeachingReadinessService."
        )


class OrchestrateContentProcessingStageService:
    def __init__(
        self,
        job_repository: Optional[ContentProcessingJobRepository] = None,
        attempt_repository: Optional[ProcessingAttemptRepository] = None,
        diagnostic_repository: Optional[ProcessingDiagnosticRepository] = None,
        stage_result_repository: Optional[ProcessingStageResultRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
        registry: Optional[StageProcessorRegistry] = None,
    ) -> None:
        self.job_repository = job_repository or DjangoContentProcessingJobRepository()
        self.attempt_repository = attempt_repository or DjangoProcessingAttemptRepository()
        self.diagnostic_repository = diagnostic_repository or DjangoProcessingDiagnosticRepository()
        self.stage_result_repository = stage_result_repository or DjangoProcessingStageResultRepository()
        self.event_publisher = event_publisher or EventPublisher()
        self.registry = registry or build_default_registry()
        self.record_diagnostic_service = RecordProcessingDiagnosticService(
            diagnostic_repository=self.diagnostic_repository,
            event_publisher=self.event_publisher,
        )
        self.fail_service = FailContentProcessingJobService(
            job_repository=self.job_repository,
            attempt_repository=self.attempt_repository,
            event_publisher=self.event_publisher,
        )

    def execute(self, job_id: str, attempt_id: str, expected_stage: str, correlation_id: str = "") -> ContentProcessingJob:
        with transaction.atomic():
            job = self.job_repository.get_for_update(job_id)
            attempt = self.attempt_repository.get_by_id(attempt_id)
            if job.status in {JobStatus.DELETED, JobStatus.CANCELLED}:
                return job
            if attempt.attempt_number != job.active_attempt_number:
                raise StaleProcessingAttemptError("A stale attempt cannot execute this stage.")
            existing_result = self.stage_result_repository.get(job_id, attempt_id, expected_stage, 1)
            if existing_result is not None:
                return job

            try:
                attempt.status = AttemptStatus.RUNNING
                first_start = attempt.started_at is None
                attempt.started_at = attempt.started_at or timezone.now()
                self.attempt_repository.save(attempt)
                job.begin_stage(expected_stage, attempt.attempt_number)
                job = self.job_repository.save(job)
                LegacyImportProjectionService().project(job)
                if first_start:
                    self.event_publisher.publish(
                        BusinessEvent.create(
                            "content_processing.attempt_started",
                            payload={
                                "job_id": str(job.id),
                                "attempt_id": str(attempt.id),
                                "resource_id": str(job.resource_id) if job.resource_id else None,
                                "stage": expected_stage,
                                "attempt_number": attempt.attempt_number,
                            },
                        )
                    )
                self.event_publisher.publish(
                    BusinessEvent.create(
                        "content_processing.stage_started",
                        payload={"job_id": str(job.id), "attempt_id": str(attempt.id), "stage": expected_stage, "progress": job.progress},
                    )
                )
                context = ProcessingStageContext(
                    job_id=str(job.id),
                    attempt_id=str(attempt.id),
                    resource_id=str(job.resource_id) if job.resource_id else None,
                    stored_file_id=str(job.stored_file_id) if job.stored_file_id else None,
                    pipeline_version=job.pipeline_version,
                    expected_stage=expected_stage,
                    correlation_id=correlation_id or attempt.correlation_id or str(uuid.uuid4()),
                )
                result = self.registry.get(expected_stage).execute(context)
                for diagnostic in result.diagnostics:
                    self.record_diagnostic_service.record(job, attempt, diagnostic)
                if job.cancellation_requested:
                    job.cancel()
                    attempt.status = AttemptStatus.CANCELLED
                    attempt.completed_at = timezone.now()
                    self.attempt_repository.save(attempt)
                    job = self.job_repository.save(job)
                    LegacyImportProjectionService().project(job)
                    self.event_publisher.publish(
                        BusinessEvent.create(
                            "content_processing.job_cancelled",
                            payload={"job_id": str(job.id), "attempt_id": str(attempt.id), "stage": expected_stage},
                        )
                    )
                    return job
                self.stage_result_repository.save(
                    ProcessingStageResult(
                        job=job,
                        attempt=attempt,
                        stage=result.completed_stage,
                        pipeline_version=job.pipeline_version,
                        result_version=1,
                        idempotency_key=f"{job.id}:{attempt.id}:{result.completed_stage}:1",
                        output_references=result.output_references,
                        checksum=result.checksum,
                    )
                )
                if result.next_stage is None:
                    job.mark_ready_for_review()
                    attempt.status = AttemptStatus.SUCCEEDED
                    attempt.completed_at = timezone.now()
                    self.attempt_repository.save(attempt)
                    job = self.job_repository.save(job)
                    LegacyImportProjectionService().project(job)
                    self.event_publisher.publish(
                        BusinessEvent.create(
                            "content_processing.stage_completed",
                            payload={"job_id": str(job.id), "attempt_id": str(attempt.id), "stage": expected_stage, "progress": job.progress},
                        )
                    )
                    self.event_publisher.publish(BusinessEvent.create("content_processing.ready_for_review", payload={"job_id": str(job.id)}))
                    return job

                job.complete_stage(expected_stage, result.next_stage, attempt.attempt_number)
                attempt.status = AttemptStatus.PENDING
                attempt.task_id = ""
                self.attempt_repository.save(attempt)
                job = self.job_repository.save(job)
                LegacyImportProjectionService().project(job)
                self.event_publisher.publish(
                    BusinessEvent.create(
                        "content_processing.stage_completed",
                        payload={"job_id": str(job.id), "attempt_id": str(attempt.id), "stage": expected_stage, "previous_stage": expected_stage, "progress": job.progress},
                    )
                )
                next_stage = result.next_stage
                self.event_publisher.publish(
                    BusinessEvent.create(
                        "content_processing.stage_progressed",
                        payload={
                            "job_id": str(job.id),
                            "attempt_id": str(attempt.id),
                            "stage": next_stage,
                            "progress": job.progress,
                        },
                    )
                )
                from apps.content_processing.infrastructure.celery.tasks import process_content_processing_stage_task

                transaction.on_commit(
                    lambda: process_content_processing_stage_task.delay(str(job.id), str(attempt.id), next_stage, context.correlation_id)
                )
                return job
            except Exception as exc:
                failure = map_exception_to_failure(exc, expected_stage)
                return self.fail_service.fail(job, attempt, failure)


def map_exception_to_failure(exc: Exception, stage: str) -> ProcessingFailure:
    message = str(exc) or "Unexpected processing failure."
    lower_message = message.lower()
    explicit_code = getattr(exc, "code", "")
    if explicit_code and explicit_code in ProcessingFailureCode.values:
        code = explicit_code
        public_messages = {
            ProcessingFailureCode.STORAGE_READ_FAILED: "The source file could not be read.",
            ProcessingFailureCode.PASSWORD_REQUIRED: "The document requires a password.",
            ProcessingFailureCode.CORRUPT_DOCUMENT: "The document is corrupt or malformed.",
            ProcessingFailureCode.NO_EXTRACTABLE_CONTENT: "No trustworthy content could be extracted.",
            ProcessingFailureCode.EXTRACTION_OUTPUT_INVALID: "The extracted document evidence was invalid.",
        }
        public_message = public_messages.get(code, "The document could not be processed.")
    elif "unsupported" in lower_message and "format" in lower_message:
        code = ProcessingFailureCode.UNSUPPORTED_FORMAT
        public_message = "The uploaded file format is not supported."
    elif "ocr" in lower_message and "unavailable" in lower_message:
        code = ProcessingFailureCode.OCR_UNAVAILABLE
        public_message = "OCR is unavailable for this document."
    elif "pdf" in lower_message:
        code = ProcessingFailureCode.PDF_PARSE_FAILED
        public_message = "The PDF could not be processed."
    elif "docx" in lower_message:
        code = ProcessingFailureCode.DOCX_PARSE_FAILED
        public_message = "The DOCX file could not be processed."
    elif "validation" in lower_message:
        code = ProcessingFailureCode.VALIDATION_FAILED
        public_message = "The content failed validation."
    elif stage == ProcessingStage.INDEXING:
        code = ProcessingFailureCode.INDEX_FAILED
        public_message = "The approved academic content could not be indexed."
    else:
        code = ProcessingFailureCode.UNEXPECTED_PROCESSING_FAILURE
        public_message = "Content processing failed unexpectedly."
    retry_classification = RetryPolicy().classify(code)
    return ProcessingFailure(
        code=code,
        stage=stage,
        public_message=public_message,
        internal_message=message,
        retry_classification=retry_classification,
        cause_category="infrastructure" if code == ProcessingFailureCode.UNEXPECTED_PROCESSING_FAILURE else "processing",
        occurred_at=timezone.now().isoformat(),
    )
