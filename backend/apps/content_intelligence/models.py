import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.academic.domain.models import LearningResource
from apps.content_intelligence.domain.exceptions import ImportLifecycleError
from apps.storage.domain.models import StoredFile


class ContentImportJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class FormatType(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_resource = models.ForeignKey(LearningResource, on_delete=models.CASCADE, related_name="content_import_jobs")
    stored_file = models.ForeignKey(StoredFile, on_delete=models.SET_NULL, null=True, blank=True, related_name="content_import_jobs")
    format_type = models.CharField(max_length=20, choices=FormatType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="content_import_jobs")
    error_message = models.TextField(blank=True)
    ocr_requested = models.BooleanField(default=False)
    ocr_used = models.BooleanField(default=False)
    extraction_confidence = models.FloatField(null=True, blank=True)
    section_confidence = models.FloatField(null=True, blank=True)
    concept_confidence = models.FloatField(null=True, blank=True)
    structural_confidence = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_intelligence_import_job"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["learning_resource"], name="ci_job_resource_idx"),
            models.Index(fields=["status"], name="ci_job_status_idx"),
            models.Index(fields=["format_type"], name="ci_job_format_idx"),
        ]

    def start(self) -> None:
        if self.status not in {self.Status.PENDING, self.Status.PROCESSING}:
            raise ImportLifecycleError(f"Cannot start content import job from {self.status}.")
        self.status = self.Status.PROCESSING
        self.started_at = self.started_at or timezone.now()

    def complete(self) -> None:
        if self.status not in {self.Status.PROCESSING, self.Status.PENDING}:
            raise ImportLifecycleError(f"Cannot complete content import job from {self.status}.")
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.error_message = ""

    def fail(self, error_message: str) -> None:
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()

    def cancel(self) -> None:
        if self.status == self.Status.COMPLETED:
            raise ImportLifecycleError("Cannot cancel a completed content import job.")
        self.status = self.Status.CANCELLED
        self.completed_at = timezone.now()

    def mark_ocr_requested(self) -> None:
        self.ocr_requested = True

    def mark_ocr_completed(self) -> None:
        self.ocr_used = True


class ParsedDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_job = models.OneToOneField(ContentImportJob, on_delete=models.CASCADE, related_name="parsed_document")
    title = models.CharField(max_length=255, blank=True)
    normalized_text = models.TextField(blank=True)
    format_type = models.CharField(max_length=20, choices=ContentImportJob.FormatType.choices)
    extraction_method = models.CharField(max_length=100)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_intelligence_parsed_document"
        ordering = ["-created_at"]


class ParsedSection(models.Model):
    class SectionType(models.TextChoices):
        FRONT_MATTER = "front_matter", "Front Matter"
        CHAPTER = "chapter", "Chapter"
        APPENDIX = "appendix", "Appendix"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parsed_document = models.ForeignKey(ParsedDocument, on_delete=models.CASCADE, related_name="sections")
    heading = models.CharField(max_length=255)
    body_text = models.TextField(blank=True)
    sequence_number = models.PositiveIntegerField()
    section_type = models.CharField(max_length=30, choices=SectionType.choices, default=SectionType.UNKNOWN)
    confidence = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_intelligence_parsed_section"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["parsed_document", "sequence_number"], name="unique_ci_parsed_section_sequence"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="ci_parsed_section_sequence_gte_1"),
        ]


class ParsedConceptCandidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parsed_section = models.ForeignKey(ParsedSection, on_delete=models.CASCADE, related_name="concept_candidates")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    learning_objective = models.TextField(blank=True)
    sequence_number = models.PositiveIntegerField()
    confidence = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_intelligence_concept_candidate"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["parsed_section", "sequence_number"], name="unique_ci_concept_candidate_sequence"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="ci_concept_candidate_sequence_gte_1"),
        ]


class ContentExtractionResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_job = models.OneToOneField(ContentImportJob, on_delete=models.CASCADE, related_name="extraction_result")
    extracted_text = models.TextField(blank=True)
    normalized_text = models.TextField(blank=True)
    extraction_method = models.CharField(max_length=100)
    sufficient_text = models.BooleanField(default=False)
    ocr_requested = models.BooleanField(default=False)
    ocr_used = models.BooleanField(default=False)
    char_count = models.PositiveIntegerField(default=0)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_intelligence_extraction_result"
        ordering = ["-created_at"]


class ContentValidationFinding(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_job = models.ForeignKey(ContentImportJob, on_delete=models.CASCADE, related_name="validation_findings")
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM)
    finding_type = models.CharField(max_length=100)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_intelligence_validation_finding"
        ordering = ["-created_at"]


class ParserPipelineRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_job = models.ForeignKey(ContentImportJob, on_delete=models.CASCADE, related_name="pipeline_runs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    current_stage = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_intelligence_pipeline_run"
        ordering = ["-created_at"]

    def start(self, stage: str) -> None:
        self.status = self.Status.RUNNING
        self.current_stage = stage
        self.started_at = self.started_at or timezone.now()

    def advance(self, stage: str) -> None:
        if self.status != self.Status.RUNNING:
            raise ImportLifecycleError(f"Cannot advance pipeline run from {self.status}.")
        self.current_stage = stage

    def complete(self) -> None:
        if self.status not in {self.Status.RUNNING, self.Status.PENDING}:
            raise ImportLifecycleError(f"Cannot complete pipeline run from {self.status}.")
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()

    def fail(self, error_message: str) -> None:
        self.status = self.Status.FAILED
        self.completed_at = timezone.now()
        metadata = dict(self.metadata or {})
        metadata["error_message"] = error_message
        self.metadata = metadata


__all__ = [
    "ContentImportJob",
    "ParsedDocument",
    "ParsedSection",
    "ParsedConceptCandidate",
    "ContentExtractionResult",
    "ContentValidationFinding",
    "ParserPipelineRun",
]
