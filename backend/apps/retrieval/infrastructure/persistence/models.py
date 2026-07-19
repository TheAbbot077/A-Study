from __future__ import annotations

import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class RetrievalReadiness(models.TextChoices):
    NOT_INDEXED = "not_indexed", "Not Indexed"
    INDEXING = "indexing", "Indexing"
    INDEXED = "indexed", "Indexed"
    STALE = "stale", "Stale"
    FAILED = "failed", "Failed"


class RetrievalChunkCollection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    population_job = models.ForeignKey("content_processing.AcademicPopulationJob", on_delete=models.PROTECT, related_name="retrieval_collections")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, related_name="retrieval_collections")
    proposal = models.ForeignKey("content_processing.AcademicImportProposal", on_delete=models.PROTECT, related_name="retrieval_collections")
    population_version = models.CharField(max_length=64)
    chunk_policy_version = models.CharField(max_length=64)
    retrieval_version = models.CharField(max_length=64)
    embedding_version = models.CharField(max_length=128)
    chunk_count = models.PositiveIntegerField(default=0)
    readiness = models.CharField(max_length=24, choices=RetrievalReadiness.choices, default=RetrievalReadiness.NOT_INDEXED)
    checksum = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "retrieval_chunk_collection"
        constraints = [models.UniqueConstraint(fields=["population_job", "population_version", "chunk_policy_version", "retrieval_version", "embedding_version"], name="retrieval_collection_identity")]


class RetrievalChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection = models.ForeignKey(RetrievalChunkCollection, on_delete=models.CASCADE, related_name="chunks", null=True, blank=True)
    generation = models.ForeignKey("RetrievalGeneration", on_delete=models.CASCADE, related_name="chunks", null=True, blank=True)
    identity_key = models.CharField(max_length=128)
    institution = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="retrieval_chunks")
    subject = models.ForeignKey("academic.Subject", on_delete=models.PROTECT, related_name="retrieval_chunks")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, related_name="retrieval_chunks")
    section = models.ForeignKey("academic.ContentSection", on_delete=models.PROTECT, related_name="retrieval_chunks")
    concept = models.ForeignKey("academic.ContentConcept", on_delete=models.PROTECT, null=True, blank=True, related_name="retrieval_chunks")
    semantic_segment = models.ForeignKey("content_processing.SemanticSegment", on_delete=models.PROTECT, null=True, blank=True, related_name="retrieval_chunks")
    proposal = models.ForeignKey("content_processing.AcademicImportProposal", on_delete=models.PROTECT, related_name="retrieval_chunks", null=True, blank=True)
    population_job = models.ForeignKey("content_processing.AcademicPopulationJob", on_delete=models.PROTECT, related_name="retrieval_chunks", null=True, blank=True)
    proposal_version = models.CharField(max_length=64)
    population_version = models.CharField(max_length=64)
    chunk_policy_version = models.CharField(max_length=64)
    retrieval_version = models.CharField(max_length=64)
    embedding_version = models.CharField(max_length=128)
    text = models.TextField()
    chunk_type = models.CharField(max_length=32)
    ordering = models.PositiveIntegerField()
    source_page_start = models.PositiveIntegerField()
    source_page_end = models.PositiveIntegerField()
    token_estimate = models.PositiveIntegerField()
    confidence = models.FloatField(default=0)
    checksum = models.CharField(max_length=128)
    embedding = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "retrieval_chunk"
        ordering = ["ordering"]
        constraints = [
            models.UniqueConstraint(fields=["collection", "ordering"], name="retrieval_chunk_order_unique"),
            models.UniqueConstraint(fields=["generation", "identity_key"], name="retrieval_generation_chunk_key_unique"),
            models.UniqueConstraint(fields=["generation", "ordering"], name="retrieval_generation_chunk_order_unique"),
            models.CheckConstraint(condition=models.Q(confidence__gte=0) & models.Q(confidence__lte=1), name="retrieval_chunk_confidence_range"),
            models.CheckConstraint(condition=models.Q(source_page_end__gte=models.F("source_page_start")), name="retrieval_chunk_page_range"),
        ]
        indexes = [models.Index(fields=["institution", "subject", "resource"], name="retrieval_academic_idx"), models.Index(fields=["section", "concept"], name="retrieval_content_idx")]

    def clean(self):
        self.text = " ".join(self.text.replace("\x00", " ").split())
        if not self.text or self.section.review_status != "approved" or (self.concept_id and self.concept.review_status != "approved"):
            raise ValidationError("Retrieval chunks require normalized approved Academic content.")


class RetrievalGeneration(models.Model):
    class Status(models.TextChoices):
        BUILDING = "building", "Building"
        VALIDATING = "validating", "Validating"
        ACTIVE = "active", "Active"
        SUPERSEDED = "superseded", "Superseded"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, related_name="retrieval_generations")
    subject = models.ForeignKey("academic.Subject", on_delete=models.PROTECT, related_name="retrieval_generations")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.BUILDING)
    source_fingerprint = models.CharField(max_length=128)
    manifest_fingerprint = models.CharField(max_length=128)
    chunk_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    promoted_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "retrieval_generation"
        constraints = [
            models.UniqueConstraint(fields=["resource"], condition=models.Q(status="active"), name="retrieval_one_active_generation"),
        ]
        indexes = [models.Index(fields=["resource", "status"], name="retrieval_gen_resource_status")]


class RetrievalSynchronizationRun(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        SYNCHRONIZING = "synchronizing", "Synchronizing"
        SYNCHRONIZED = "synchronized", "Synchronized"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    academic_population_run = models.ForeignKey("academic_review.AcademicPopulationRun", on_delete=models.PROTECT, related_name="retrieval_synchronization_runs")
    approved_projection_id = models.UUIDField()
    processing_job_id = models.UUIDField(null=True, blank=True)
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, related_name="retrieval_synchronization_runs")
    subject = models.ForeignKey("academic.Subject", on_delete=models.PROTECT, related_name="retrieval_synchronization_runs")
    requested_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="retrieval_synchronization_runs")
    trigger = models.CharField(max_length=32, default="staff")
    reason = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=128, unique=True)
    request_fingerprint = models.CharField(max_length=128)
    source_fingerprint = models.CharField(max_length=128)
    manifest_fingerprint = models.CharField(max_length=128)
    retrieval_generation = models.ForeignKey(RetrievalGeneration, on_delete=models.PROTECT, null=True, blank=True, related_name="synchronization_runs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    planned_chunk_count = models.PositiveIntegerField(default=0)
    indexed_chunk_count = models.PositiveIntegerField(default=0)
    keyword_indexed_count = models.PositiveIntegerField(default=0)
    vector_indexed_count = models.PositiveIntegerField(default=0)
    failed_chunk_count = models.PositiveIntegerField(default=0)
    citation_coverage = models.FloatField(default=0)
    prior_run = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="retries")
    failure_code = models.CharField(max_length=64, blank=True)
    failure_message = models.CharField(max_length=500, blank=True)
    version = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retrieval_synchronization_run"
        indexes = [
            models.Index(fields=["academic_population_run", "status"], name="retrieval_sync_population"),
            models.Index(fields=["resource", "status"], name="retrieval_sync_resource"),
            models.Index(fields=["manifest_fingerprint", "status"], name="retrieval_sync_manifest"),
        ]

    def start(self):
        if self.status != self.Status.PLANNED:
            raise ValidationError("Only a planned synchronization may start.")
        self.status, self.started_at = self.Status.SYNCHRONIZING, timezone.now()
        self.version += 1

    def complete(self):
        if self.status != self.Status.SYNCHRONIZING:
            raise ValidationError("Only a synchronizing run may complete.")
        if not self.planned_chunk_count or self.indexed_chunk_count != self.planned_chunk_count:
            raise ValidationError("INDEX_RECONCILIATION_FAILED")
        if self.keyword_indexed_count != self.planned_chunk_count or self.vector_indexed_count != self.planned_chunk_count:
            raise ValidationError("INDEX_RECONCILIATION_FAILED")
        if self.citation_coverage != 1:
            raise ValidationError("CITATION_COVERAGE_FAILED")
        self.status, self.completed_at = self.Status.SYNCHRONIZED, timezone.now()
        self.version += 1

    def fail(self, code, message=""):
        if self.status in {self.Status.SYNCHRONIZED, self.Status.FAILED}:
            raise ValidationError("Terminal synchronization runs are immutable.")
        if not (code or "").strip():
            raise ValidationError("A stable failure code is required.")
        self.status, self.failure_code, self.failure_message = self.Status.FAILED, code, message
        self.failed_at = timezone.now()
        self.version += 1


class RetrievalIndexJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    population_job = models.ForeignKey("content_processing.AcademicPopulationJob", on_delete=models.PROTECT, related_name="retrieval_index_jobs")
    collection = models.ForeignKey(RetrievalChunkCollection, on_delete=models.PROTECT, null=True, blank=True, related_name="index_jobs")
    retrieval_version = models.CharField(max_length=64)
    embedding_version = models.CharField(max_length=128)
    status = models.CharField(max_length=24, choices=RetrievalReadiness.choices, default=RetrievalReadiness.NOT_INDEXED)
    chunk_count = models.PositiveIntegerField(default=0)
    indexed_count = models.PositiveIntegerField(default=0)
    warnings = models.JSONField(default=list, blank=True)
    statistics = models.JSONField(default=dict, blank=True)
    diagnostics = models.JSONField(default=list, blank=True)
    failure_code = models.CharField(max_length=128, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "retrieval_index_job"
        constraints = [models.UniqueConstraint(fields=["population_job", "retrieval_version", "embedding_version"], name="retrieval_index_job_identity")]

    def start(self):
        self.status, self.started_at, self.failure_code = RetrievalReadiness.INDEXING, timezone.now(), ""

    def complete(self, indexed_count, checksum):
        if indexed_count != self.chunk_count:
            raise ValidationError("Every retrieval chunk must be indexed before readiness.")
        self.status, self.indexed_count, self.checksum, self.completed_at = RetrievalReadiness.INDEXED, indexed_count, checksum, timezone.now()

    def fail(self, code):
        self.status, self.failure_code, self.completed_at = RetrievalReadiness.FAILED, code, timezone.now()


class GroundingPackage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query_text = models.TextField()
    retrieved_chunk_ids = models.JSONField(default=list)
    confidence_scores = models.JSONField(default=list)
    ranking_metadata = models.JSONField(default=dict)
    retrieval_rationale = models.TextField(blank=True)
    metadata_filters = models.JSONField(default=dict)
    proposal_versions = models.JSONField(default=list)
    population_versions = models.JSONField(default=list)
    token_budget_summary = models.JSONField(default=dict)
    retrieval_statistics = models.JSONField(default=dict)
    diagnostics = models.JSONField(default=list)
    checksum = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "retrieval_grounding_package"


class GroundingCitation(models.Model):
    package = models.ForeignKey(GroundingPackage, on_delete=models.CASCADE, related_name="citations")
    chunk = models.ForeignKey(RetrievalChunk, on_delete=models.PROTECT, related_name="grounding_citations")
    institution = models.ForeignKey("users.Institution", on_delete=models.PROTECT)
    subject = models.ForeignKey("academic.Subject", on_delete=models.PROTECT)
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT)
    section = models.ForeignKey("academic.ContentSection", on_delete=models.PROTECT)
    concept = models.ForeignKey("academic.ContentConcept", on_delete=models.PROTECT, null=True, blank=True)
    semantic_segment = models.ForeignKey("content_processing.SemanticSegment", on_delete=models.PROTECT, null=True, blank=True)
    proposal = models.ForeignKey("content_processing.AcademicImportProposal", on_delete=models.PROTECT)
    population_job = models.ForeignKey("content_processing.AcademicPopulationJob", on_delete=models.PROTECT)
    source_page_start = models.PositiveIntegerField()
    source_page_end = models.PositiveIntegerField()
    rank = models.PositiveIntegerField()
    score = models.FloatField()

    class Meta:
        db_table = "retrieval_grounding_citation"
        constraints = [models.UniqueConstraint(fields=["package", "chunk"], name="retrieval_citation_unique")]


class RetrievalStatistic(models.Model):
    index_job = models.OneToOneField(RetrievalIndexJob, on_delete=models.CASCADE, related_name="statistic_record")
    collection = models.ForeignKey(RetrievalChunkCollection, on_delete=models.CASCADE, related_name="statistic_records")
    chunk_count = models.PositiveIntegerField(default=0)
    indexed_count = models.PositiveIntegerField(default=0)
    embedding_batch_count = models.PositiveIntegerField(default=0)
    ranking_policy_version = models.CharField(max_length=64)
    values = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "retrieval_statistic"


class RetrievalDiagnostic(models.Model):
    index_job = models.ForeignKey(RetrievalIndexJob, on_delete=models.CASCADE, null=True, blank=True, related_name="diagnostic_records")
    grounding_package = models.ForeignKey(GroundingPackage, on_delete=models.CASCADE, null=True, blank=True, related_name="diagnostic_records")
    severity = models.CharField(max_length=16)
    code = models.CharField(max_length=128)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "retrieval_diagnostic"

    def clean(self):
        if bool(self.index_job_id) == bool(self.grounding_package_id):
            raise ValidationError("A retrieval diagnostic belongs to exactly one aggregate.")
