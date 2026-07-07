import uuid

from django.db import models

from apps.storage.domain.models import StoredFile
from apps.users.domain.models import Institution, User


class Subject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="subjects")
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_subject"
        ordering = ["code"]
        unique_together = (("institution", "code"),)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code} - {self.name}"


class Curriculum(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="curricula")
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name="curricula")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, default="1.0")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_curriculum"
        ordering = ["subject", "name", "version"]
        constraints = [
            models.UniqueConstraint(fields=["subject", "institution", "version"], name="unique_subject_institution_version"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.subject.code} / {self.name} v{self.version}"


class CurriculumUnit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    curriculum = models.ForeignKey(Curriculum, on_delete=models.CASCADE, related_name="units")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sequence_number = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_curriculum_unit"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["curriculum", "sequence_number"], name="unique_curriculum_sequence_number"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="curriculum_unit_sequence_number_gte_1"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.curriculum.name} :: {self.sequence_number} - {self.title}"


class LearningResource(models.Model):
    class ResourceType(models.TextChoices):
        TEXTBOOK = "textbook", "Textbook"
        NOTES = "notes", "Notes"
        GUIDE = "guide", "Guide"
        REFERENCE = "reference", "Reference"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name="learning_resources")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="learning_resources")
    curriculum = models.ForeignKey(Curriculum, on_delete=models.SET_NULL, null=True, blank=True, related_name="learning_resources")
    curriculum_unit = models.ForeignKey(CurriculumUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name="learning_resources")
    stored_file = models.ForeignKey(StoredFile, on_delete=models.SET_NULL, null=True, blank=True, related_name="learning_resources")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=50, choices=ResourceType.choices, default=ResourceType.OTHER)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.DRAFT)
    source_label = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_learning_resource"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["institution"], name="acad_lr_inst_idx"),
            models.Index(fields=["subject"], name="acad_lr_subject_idx"),
            models.Index(fields=["curriculum"], name="acad_lr_curr_idx"),
            models.Index(fields=["curriculum_unit"], name="acad_lr_unit_idx"),
            models.Index(fields=["resource_type"], name="acad_lr_type_idx"),
            models.Index(fields=["status"], name="acad_lr_status_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title


class ContentSection(models.Model):
    class ReviewStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    class QualityStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        LOW = "low", "Low"
        ACCEPTABLE = "acceptable", "Acceptable"
        HIGH = "high", "High"
        NEEDS_ATTENTION = "needs_attention", "Needs Attention"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_resource = models.ForeignKey(LearningResource, on_delete=models.CASCADE, related_name="content_sections")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sequence_number = models.PositiveIntegerField()
    review_status = models.CharField(max_length=50, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    quality_status = models.CharField(max_length=50, choices=QualityStatus.choices, default=QualityStatus.UNKNOWN)
    review_notes = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_content_sections")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_content_section"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["learning_resource", "sequence_number"], name="unique_learning_resource_sequence_number"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="content_section_sequence_number_gte_1"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title


class ContentConcept(models.Model):
    class ReviewStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    class QualityStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        LOW = "low", "Low"
        ACCEPTABLE = "acceptable", "Acceptable"
        HIGH = "high", "High"
        NEEDS_ATTENTION = "needs_attention", "Needs Attention"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_section = models.ForeignKey(ContentSection, on_delete=models.CASCADE, related_name="content_concepts")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    learning_objective = models.TextField(blank=True)
    sequence_number = models.PositiveIntegerField()
    review_status = models.CharField(max_length=50, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    quality_status = models.CharField(max_length=50, choices=QualityStatus.choices, default=QualityStatus.UNKNOWN)
    review_notes = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_content_concepts")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_content_concept"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["content_section", "sequence_number"], name="unique_content_section_sequence_number"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="content_concept_sequence_number_gte_1"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title


class ResourceIngestionJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class SourceType(models.TextChoices):
        MANUAL = "manual", "Manual"
        UPLOAD = "upload", "Upload"
        IMPORT = "import", "Import"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_resource = models.ForeignKey(LearningResource, on_delete=models.CASCADE, related_name="ingestion_jobs")
    stored_file = models.ForeignKey(StoredFile, on_delete=models.SET_NULL, null=True, blank=True, related_name="ingestion_jobs")
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    source_type = models.CharField(max_length=50, choices=SourceType.choices, default=SourceType.MANUAL)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="ingestion_jobs")
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_resource_ingestion_job"
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.learning_resource.title} [{self.status}]"


__all__ = ["Subject", "Curriculum", "CurriculumUnit", "LearningResource", "ContentSection", "ContentConcept", "ResourceIngestionJob"]
