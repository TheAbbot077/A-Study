from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.academic.domain.models import LearningResource
from apps.content_intelligence.models import ContentImportJob
from apps.storage.domain.models import StoredFile
from .exceptions import ProcessingLifecycleError, StaleProcessingAttemptError


class JobStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    READY_FOR_REVIEW = "ready_for_review", "Ready For Review"
    READY_FOR_TEACHING = "ready_for_teaching", "Ready For Teaching"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    DELETED = "deleted", "Deleted"


class ProcessingStage(models.TextChoices):
    CREATED = "created", "Created"
    QUEUED = "queued", "Queued"
    INSPECTING = "inspecting", "Inspecting"
    EXTRACTING = "extracting", "Extracting"
    STRUCTURING = "structuring", "Structuring"
    SEGMENTING = "segmenting", "Segmenting"
    VALIDATING = "validating", "Validating"
    POPULATING = "populating", "Populating"
    INDEXING = "indexing", "Indexing"


class AttemptStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class DiagnosticSeverity(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"
    FATAL = "fatal", "Fatal"


class RetryClassification(models.TextChoices):
    NON_RETRYABLE = "non_retryable", "Non Retryable"
    RETRYABLE_SAME_STAGE = "retryable_same_stage", "Retryable Same Stage"
    RETRYABLE_FROM_PRIOR_STAGE = "retryable_from_prior_stage", "Retryable From Prior Stage"
    REQUIRES_OPERATOR_ACTION = "requires_operator_action", "Requires Operator Action"


class AttemptTrigger(models.TextChoices):
    INITIAL_UPLOAD = "initial_upload", "Initial Upload"
    AUTOMATIC_RETRY = "automatic_retry", "Automatic Retry"
    MANUAL_RETRY = "manual_retry", "Manual Retry"
    FULL_REPROCESS = "full_reprocess", "Full Reprocess"
    ADMIN_REPROCESS = "admin_reprocess", "Admin Reprocess"


class ProcessingFailureCode(models.TextChoices):
    STORAGE_READ_FAILED = "storage_read_failed", "Storage Read Failed"
    UNSUPPORTED_FORMAT = "unsupported_format", "Unsupported Format"
    FILE_INSPECTION_FAILED = "file_inspection_failed", "File Inspection Failed"
    ENCRYPTED_DOCUMENT = "encrypted_document", "Encrypted Document"
    PASSWORD_REQUIRED = "password_required", "Password Required"
    CORRUPT_DOCUMENT = "corrupt_document", "Corrupt Document"
    PDF_PARSE_FAILED = "pdf_parse_failed", "PDF Parse Failed"
    DOCX_PARSE_FAILED = "docx_parse_failed", "DOCX Parse Failed"
    OCR_UNAVAILABLE = "ocr_unavailable", "OCR Unavailable"
    OCR_FAILED = "ocr_failed", "OCR Failed"
    NO_EXTRACTABLE_CONTENT = "no_extractable_content", "No Extractable Content"
    EXTRACTION_OUTPUT_INVALID = "extraction_output_invalid", "Extraction Output Invalid"
    EXTRACTION_RESULT_MISSING = "extraction_result_missing", "Extraction Result Missing"
    EXTRACTION_RESULT_INVALID = "extraction_result_invalid", "Extraction Result Invalid"
    HIERARCHY_RECONSTRUCTION_FAILED = "hierarchy_reconstruction_failed", "Hierarchy Reconstruction Failed"
    HIERARCHY_OUTPUT_INVALID = "hierarchy_output_invalid", "Hierarchy Output Invalid"
    SEGMENTATION_FAILED = "segmentation_failed", "Segmentation Failed"
    SEGMENTATION_OUTPUT_INVALID = "segmentation_output_invalid", "Segmentation Output Invalid"
    NO_MEANINGFUL_STRUCTURE = "no_meaningful_structure", "No Meaningful Structure"
    NO_MEANINGFUL_SEGMENTS = "no_meaningful_segments", "No Meaningful Segments"
    STRUCTURE_LIMIT_EXCEEDED = "structure_limit_exceeded", "Structure Limit Exceeded"
    SEGMENT_LIMIT_EXCEEDED = "segment_limit_exceeded", "Segment Limit Exceeded"
    PROPOSAL_GENERATION_FAILED = "proposal_generation_failed", "Proposal Generation Failed"
    SECTION_VALIDATION_FAILED = "section_validation_failed", "Section Validation Failed"
    CONCEPT_VALIDATION_FAILED = "concept_validation_failed", "Concept Validation Failed"
    PROPOSAL_APPROVAL_FAILED = "proposal_approval_failed", "Proposal Approval Failed"
    POPULATION_FAILED = "population_failed", "Population Failed"
    POPULATION_CONFLICT = "population_conflict", "Population Conflict"
    REVIEW_REQUIRED = "review_required", "Review Required"
    HIERARCHY_UNRESOLVED = "hierarchy_unresolved", "Hierarchy Unresolved"
    NO_ACADEMIC_CONTENT = "no_academic_content", "No Academic Content"
    VALIDATION_FAILED = "validation_failed", "Validation Failed"
    ACADEMIC_IMPORT_FAILED = "academic_import_failed", "Academic Import Failed"
    EMBEDDING_FAILED = "embedding_failed", "Embedding Failed"
    INDEXING_FAILED = "indexing_failed", "Indexing Failed"
    CHUNK_BUILD_FAILED = "chunk_build_failed", "Chunk Build Failed"
    INDEX_FAILED = "index_failed", "Index Failed"
    GROUNDING_FAILED = "grounding_failed", "Grounding Failed"
    RETRIEVAL_CONFIGURATION_INVALID = "retrieval_configuration_invalid", "Retrieval Configuration Invalid"
    PROVIDER_UNAVAILABLE = "provider_unavailable", "Provider Unavailable"
    INDEX_VERSION_CONFLICT = "index_version_conflict", "Index Version Conflict"
    PROCESSING_TIMEOUT = "processing_timeout", "Processing Timeout"
    PROCESSING_CANCELLED = "processing_cancelled", "Processing Cancelled"
    UNEXPECTED_PROCESSING_FAILURE = "unexpected_processing_failure", "Unexpected Processing Failure"


@dataclass(frozen=True)
class ProcessingFailure:
    code: str
    stage: str
    public_message: str
    internal_message: str = ""
    retry_classification: str = RetryClassification.NON_RETRYABLE
    cause_category: str = ""
    occurred_at: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "stage": self.stage,
            "public_message": self.public_message,
            "internal_message": self.internal_message,
            "retry_classification": self.retry_classification,
            "cause_category": self.cause_category,
            "occurred_at": self.occurred_at or timezone.now().isoformat(),
        }


class ContentProcessingJob(models.Model):
    PIPELINE_VERSION = "content-processing-v1"
    STAGE_SEQUENCE = [
        ProcessingStage.CREATED,
        ProcessingStage.QUEUED,
        ProcessingStage.INSPECTING,
        ProcessingStage.EXTRACTING,
        ProcessingStage.STRUCTURING,
        ProcessingStage.SEGMENTING,
        ProcessingStage.VALIDATING,
        ProcessingStage.POPULATING,
        ProcessingStage.INDEXING,
    ]
    STAGE_PROGRESS = {
        ProcessingStage.CREATED: 0,
        ProcessingStage.QUEUED: 5,
        ProcessingStage.INSPECTING: 10,
        ProcessingStage.EXTRACTING: 25,
        ProcessingStage.STRUCTURING: 45,
        ProcessingStage.SEGMENTING: 60,
        ProcessingStage.VALIDATING: 72,
        ProcessingStage.POPULATING: 82,
        ProcessingStage.INDEXING: 92,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.ForeignKey(LearningResource, on_delete=models.SET_NULL, null=True, blank=True, related_name="content_processing_jobs")
    stored_file = models.ForeignKey(StoredFile, on_delete=models.SET_NULL, null=True, blank=True, related_name="content_processing_jobs")
    legacy_import_job = models.OneToOneField(ContentImportJob, on_delete=models.SET_NULL, null=True, blank=True, related_name="processing_job")
    pipeline_version = models.CharField(max_length=100, default=PIPELINE_VERSION)
    status = models.CharField(max_length=50, choices=JobStatus.choices, default=JobStatus.ACTIVE)
    current_stage = models.CharField(max_length=50, choices=ProcessingStage.choices, default=ProcessingStage.CREATED)
    progress = models.PositiveIntegerField(default=0)
    active_attempt_number = models.PositiveIntegerField(default=0)
    cancellation_requested = models.BooleanField(default=False)
    failure = models.JSONField(default=dict, blank=True)
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_transition_at = models.DateTimeField(default=timezone.now)
    transition_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_processing_job"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(progress__gte=0) & models.Q(progress__lte=100), name="cp_job_progress_range"),
            models.UniqueConstraint(
                fields=["resource", "stored_file", "pipeline_version"],
                condition=~models.Q(status=JobStatus.DELETED),
                name="cp_job_active_identity_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="cp_job_status_idx"),
            models.Index(fields=["current_stage"], name="cp_job_stage_idx"),
            models.Index(fields=["resource"], name="cp_job_resource_idx"),
            models.Index(fields=["stored_file"], name="cp_job_file_idx"),
            models.Index(fields=["pipeline_version"], name="cp_job_pipeline_idx"),
        ]

    def flattened_status(self) -> str:
        return self.current_stage.upper() if self.status == JobStatus.ACTIVE else self.status.upper()

    def queue(self) -> None:
        self._ensure_mutable()
        if self.current_stage not in {ProcessingStage.CREATED, ProcessingStage.QUEUED}:
            raise ProcessingLifecycleError(f"Cannot queue processing job from stage {self.current_stage}.")
        self.current_stage = ProcessingStage.QUEUED
        self.progress = self.STAGE_PROGRESS[ProcessingStage.QUEUED]
        self.queued_at = self.queued_at or timezone.now()
        self.last_transition_at = timezone.now()
        self.transition_version += 1

    def begin_stage(self, stage: str, attempt_number: int) -> None:
        self._ensure_mutable()
        if attempt_number != self.active_attempt_number:
            raise StaleProcessingAttemptError("Only the active attempt may advance the processing job.")
        if self.cancellation_requested:
            raise ProcessingLifecycleError("Processing has been cancelled.")
        expected_current = ProcessingStage.QUEUED if stage == ProcessingStage.INSPECTING else self._previous_stage(stage)
        if self.current_stage not in {expected_current, stage}:
            raise ProcessingLifecycleError(f"Cannot begin stage {stage} from {self.current_stage}.")
        self.current_stage = stage
        self.progress = max(self.progress, self.STAGE_PROGRESS.get(stage, self.progress))
        self.started_at = self.started_at or timezone.now()
        self.last_transition_at = timezone.now()
        self.transition_version += 1

    def report_progress(self, progress: int, attempt_number: int) -> None:
        self._ensure_mutable()
        if attempt_number != self.active_attempt_number:
            raise StaleProcessingAttemptError("Only the active attempt may report progress.")
        if progress < self.progress or progress < 0 or progress > 100:
            raise ProcessingLifecycleError("Progress must be monotonic within an attempt and stay within 0-100.")
        self.progress = progress
        self.last_transition_at = timezone.now()

    def complete_stage(self, stage: str, next_stage: str | None, attempt_number: int) -> None:
        self._ensure_mutable()
        if attempt_number != self.active_attempt_number:
            raise StaleProcessingAttemptError("Only the active attempt may complete a stage.")
        if self.current_stage != stage:
            raise ProcessingLifecycleError(f"Cannot complete stage {stage} from {self.current_stage}.")
        if self.cancellation_requested:
            self.cancel()
            return
        if next_stage is None:
            self.mark_ready_for_review()
            return
        self.current_stage = next_stage
        self.progress = max(self.progress, self.STAGE_PROGRESS.get(next_stage, self.progress))
        self.last_transition_at = timezone.now()
        self.transition_version += 1

    def fail(self, failure: ProcessingFailure, attempt_number: int) -> None:
        if attempt_number != self.active_attempt_number:
            raise StaleProcessingAttemptError("Only the active attempt may fail the job.")
        self.status = JobStatus.FAILED
        self.failure = failure.to_dict()
        self.completed_at = timezone.now()
        self.last_transition_at = timezone.now()
        self.transition_version += 1

    def request_cancellation(self) -> None:
        self._ensure_mutable()
        self.cancellation_requested = True
        self.last_transition_at = timezone.now()

    def cancel(self) -> None:
        self.status = JobStatus.CANCELLED
        self.failure = ProcessingFailure(
            code=ProcessingFailureCode.PROCESSING_CANCELLED,
            stage=self.current_stage,
            public_message="Processing was cancelled.",
            retry_classification=RetryClassification.REQUIRES_OPERATOR_ACTION,
            cause_category="operator",
        ).to_dict()
        self.completed_at = timezone.now()
        self.last_transition_at = timezone.now()
        self.transition_version += 1

    def begin_retry(self, attempt_number: int, restart_stage: str) -> None:
        if self.status not in {JobStatus.FAILED, JobStatus.CANCELLED}:
            raise ProcessingLifecycleError("Only failed or cancelled jobs may be retried.")
        self.status = JobStatus.ACTIVE
        self.current_stage = ProcessingStage.QUEUED
        self.progress = self.STAGE_PROGRESS[ProcessingStage.QUEUED]
        self.active_attempt_number = attempt_number
        self.cancellation_requested = False
        self.failure = {}
        self.completed_at = None
        self.last_transition_at = timezone.now()
        self.transition_version += 1

    def mark_ready_for_review(self) -> None:
        self._ensure_mutable()
        self.status = JobStatus.READY_FOR_REVIEW
        self.progress = 98
        self.completed_at = timezone.now()
        self.last_transition_at = timezone.now()
        self.transition_version += 1

    def grant_teaching_readiness(self, evaluation_id: str) -> None:
        if self.status != JobStatus.READY_FOR_REVIEW:
            raise ProcessingLifecycleError("Content must be ready for review before teaching readiness can be marked.")
        if not (evaluation_id or "").strip():
            raise ProcessingLifecycleError("A successful teaching-readiness evaluation is required.")
        self.status = JobStatus.READY_FOR_TEACHING
        self.progress = 100
        self.completed_at = timezone.now()
        self.last_transition_at = timezone.now()
        self.transition_version += 1

    def mark_deleted(self) -> None:
        self.status = JobStatus.DELETED
        self.cancellation_requested = True
        self.completed_at = timezone.now()
        self.last_transition_at = timezone.now()
        self.transition_version += 1

    def _ensure_mutable(self) -> None:
        if self.status in {JobStatus.DELETED, JobStatus.READY_FOR_TEACHING}:
            raise ProcessingLifecycleError(f"Cannot mutate a processing job in status {self.status}.")

    def _previous_stage(self, stage: str) -> str:
        index = self.STAGE_SEQUENCE.index(stage)
        if index == 0:
            return stage
        return self.STAGE_SEQUENCE[index - 1]


class ProcessingAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(ContentProcessingJob, on_delete=models.CASCADE, related_name="attempts")
    attempt_number = models.PositiveIntegerField()
    trigger = models.CharField(max_length=50, choices=AttemptTrigger.choices)
    restart_stage = models.CharField(max_length=50, choices=ProcessingStage.choices, default=ProcessingStage.INSPECTING)
    status = models.CharField(max_length=50, choices=AttemptStatus.choices, default=AttemptStatus.PENDING)
    failure = models.JSONField(default=dict, blank=True)
    correlation_id = models.CharField(max_length=255, blank=True)
    task_id = models.CharField(max_length=255, blank=True)
    initiated_by_actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="content_processing_attempts")
    diagnostic_summary = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_attempt"
        ordering = ["-attempt_number"]
        constraints = [
            models.UniqueConstraint(fields=["job", "attempt_number"], name="cp_attempt_number_unique"),
        ]


class ProcessingDiagnostic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(ContentProcessingJob, on_delete=models.CASCADE, related_name="diagnostics")
    attempt = models.ForeignKey(ProcessingAttempt, on_delete=models.CASCADE, related_name="diagnostics")
    stage = models.CharField(max_length=50, choices=ProcessingStage.choices)
    severity = models.CharField(max_length=20, choices=DiagnosticSeverity.choices)
    code = models.CharField(max_length=100)
    public_message = models.TextField()
    internal_message = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    source_component = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_diagnostic"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["job", "severity"], name="cp_diag_job_severity_idx"),
            models.Index(fields=["attempt"], name="cp_diag_attempt_idx"),
        ]


class ProcessingStageResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(ContentProcessingJob, on_delete=models.CASCADE, related_name="stage_results")
    attempt = models.ForeignKey(ProcessingAttempt, on_delete=models.CASCADE, related_name="stage_results")
    stage = models.CharField(max_length=50, choices=ProcessingStage.choices)
    pipeline_version = models.CharField(max_length=100)
    result_version = models.PositiveIntegerField(default=1)
    idempotency_key = models.CharField(max_length=255)
    output_references = models.JSONField(default=dict, blank=True)
    checksum = models.CharField(max_length=255, blank=True)
    completed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_stage_result"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["job", "attempt", "stage", "result_version"], name="cp_stage_result_unique"),
        ]


__all__ = [
    "ContentProcessingJob",
    "ProcessingAttempt",
    "ProcessingDiagnostic",
    "ProcessingStageResult",
    "JobStatus",
    "ProcessingStage",
    "AttemptStatus",
    "DiagnosticSeverity",
    "RetryClassification",
    "AttemptTrigger",
    "ProcessingFailureCode",
    "ProcessingFailure",
]
