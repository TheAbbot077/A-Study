from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ProposalReviewState(models.TextChoices):
    DRAFT = "draft", "Draft"
    READY_FOR_REVIEW = "ready_for_review", "Ready For Review"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    APPROVED_WITH_EDITS = "approved_with_edits", "Approved With Edits"
    REJECTED = "rejected", "Rejected"
    SUPERSEDED = "superseded", "Superseded"
    ARCHIVED = "archived", "Archived"


class ProposalDecisionType(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    APPROVED_WITH_EDITS = "approved_with_edits", "Approved With Edits"
    REJECTED = "rejected", "Rejected"
    SUPERSEDED = "superseded", "Superseded"


class PopulationState(models.TextChoices):
    NOT_READY = "not_ready", "Not Ready"
    READY_FOR_POPULATION = "ready_for_population", "Ready For Population"
    POPULATION_IN_PROGRESS = "population_in_progress", "Population In Progress"
    POPULATED = "populated", "Populated"
    POPULATION_FAILED = "population_failed", "Population Failed"


class PopulationJobStatus(models.TextChoices):
    READY_FOR_POPULATION = "ready_for_population", "Ready For Population"
    POPULATION_IN_PROGRESS = "population_in_progress", "Population In Progress"
    POPULATED = "populated", "Populated"
    POPULATION_FAILED = "population_failed", "Population Failed"


class ProposalItemType(models.TextChoices):
    SECTION = "section", "Section"
    CONCEPT = "concept", "Concept"


class AcademicImportProposal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("content_processing.ContentProcessingJob", on_delete=models.CASCADE, related_name="academic_import_proposals")
    attempt = models.ForeignKey("content_processing.ProcessingAttempt", on_delete=models.CASCADE, related_name="academic_import_proposals")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, related_name="academic_import_proposals")
    document_hierarchy = models.ForeignKey("content_processing.DocumentHierarchy", on_delete=models.PROTECT, related_name="academic_import_proposals")
    document_segmentation = models.ForeignKey("content_processing.DocumentSegmentation", on_delete=models.PROTECT, related_name="academic_import_proposals")
    pipeline_version = models.CharField(max_length=100)
    proposal_engine = models.CharField(max_length=128)
    proposal_version = models.CharField(max_length=64)
    configuration_version = models.CharField(max_length=64)
    review_state = models.CharField(max_length=32, choices=ProposalReviewState.choices, default=ProposalReviewState.DRAFT)
    decision = models.CharField(max_length=32, choices=ProposalDecisionType.choices, default=ProposalDecisionType.PENDING)
    population_state = models.CharField(max_length=32, choices=PopulationState.choices, default=PopulationState.NOT_READY)
    confidence = models.FloatField(default=0)
    statistics = models.JSONField(default=dict, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    review_required = models.BooleanField(default=True)
    result_checksum = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "content_processing_academic_import_proposal"
        constraints = [
            models.UniqueConstraint(fields=["job", "attempt", "document_hierarchy", "document_segmentation", "proposal_version", "pipeline_version"], name="cp_proposal_identity_unique"),
            models.CheckConstraint(condition=models.Q(confidence__gte=0) & models.Q(confidence__lte=1), name="cp_proposal_confidence_range"),
        ]

    def begin_review(self) -> None:
        if self.review_state != ProposalReviewState.READY_FOR_REVIEW:
            raise ValidationError("Only a ready proposal may enter review.")
        self.review_state = ProposalReviewState.UNDER_REVIEW

    def approve(self, with_edits: bool = False) -> None:
        if self.review_state not in {ProposalReviewState.READY_FOR_REVIEW, ProposalReviewState.UNDER_REVIEW}:
            raise ValidationError("Only a reviewable proposal may be approved.")
        self.review_state = ProposalReviewState.APPROVED_WITH_EDITS if with_edits else ProposalReviewState.APPROVED
        self.decision = ProposalDecisionType.APPROVED_WITH_EDITS if with_edits else ProposalDecisionType.APPROVED
        self.population_state = PopulationState.READY_FOR_POPULATION

    def reject(self) -> None:
        if self.review_state not in {ProposalReviewState.READY_FOR_REVIEW, ProposalReviewState.UNDER_REVIEW}:
            raise ValidationError("Only a reviewable proposal may be rejected.")
        self.review_state = ProposalReviewState.REJECTED
        self.decision = ProposalDecisionType.REJECTED
        self.population_state = PopulationState.NOT_READY

    def supersede(self) -> None:
        if self.review_state in {ProposalReviewState.ARCHIVED, ProposalReviewState.SUPERSEDED}:
            raise ValidationError("The proposal is already terminal.")
        self.review_state = ProposalReviewState.SUPERSEDED
        self.decision = ProposalDecisionType.SUPERSEDED
        self.population_state = PopulationState.NOT_READY


class ProposedSection(models.Model):
    proposal = models.ForeignKey(AcademicImportProposal, on_delete=models.CASCADE, related_name="proposed_sections")
    title = models.CharField(max_length=255)
    normalized_title = models.CharField(max_length=255)
    parent_reference = models.CharField(max_length=128, blank=True)
    hierarchy_node = models.ForeignKey("content_processing.DocumentHierarchyNode", on_delete=models.PROTECT, related_name="proposed_sections")
    ordering = models.PositiveIntegerField()
    source_page_start = models.PositiveIntegerField(null=True, blank=True)
    source_page_end = models.PositiveIntegerField(null=True, blank=True)
    confidence = models.FloatField(default=0)
    warnings = models.JSONField(default=list, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    populated_section = models.OneToOneField("academic.ContentSection", on_delete=models.SET_NULL, null=True, blank=True, related_name="source_proposal_section")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_proposed_section"
        constraints = [
            models.UniqueConstraint(fields=["proposal", "ordering"], name="cp_proposed_section_order_unique"),
            models.UniqueConstraint(fields=["proposal", "normalized_title"], name="cp_proposed_section_title_unique"),
            models.CheckConstraint(condition=models.Q(confidence__gte=0) & models.Q(confidence__lte=1), name="cp_proposed_section_confidence_range"),
            models.CheckConstraint(condition=models.Q(ordering__gte=1), name="cp_proposed_section_order_gte_1"),
        ]


class ProposedConcept(models.Model):
    proposal = models.ForeignKey(AcademicImportProposal, on_delete=models.CASCADE, related_name="proposed_concepts")
    proposed_section = models.ForeignKey(ProposedSection, on_delete=models.CASCADE, related_name="proposed_concepts")
    semantic_segment = models.ForeignKey("content_processing.SemanticSegment", on_delete=models.PROTECT, related_name="proposed_concepts")
    title = models.CharField(max_length=255)
    normalized_title = models.CharField(max_length=255)
    supporting_text = models.TextField()
    explanation = models.TextField()
    ordering = models.PositiveIntegerField()
    source_page_start = models.PositiveIntegerField(null=True, blank=True)
    source_page_end = models.PositiveIntegerField(null=True, blank=True)
    confidence = models.FloatField(default=0)
    warnings = models.JSONField(default=list, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    populated_concept = models.OneToOneField("academic.ContentConcept", on_delete=models.SET_NULL, null=True, blank=True, related_name="source_proposal_concept")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_proposed_concept"
        constraints = [
            models.UniqueConstraint(fields=["proposed_section", "ordering"], name="cp_proposed_concept_order_unique"),
            models.UniqueConstraint(fields=["proposed_section", "normalized_title"], name="cp_proposed_concept_title_unique"),
            models.CheckConstraint(condition=models.Q(confidence__gte=0) & models.Q(confidence__lte=1), name="cp_proposed_concept_confidence_range"),
            models.CheckConstraint(condition=models.Q(ordering__gte=1), name="cp_proposed_concept_order_gte_1"),
        ]


class ProposalEvidence(models.Model):
    proposal = models.ForeignKey(AcademicImportProposal, on_delete=models.CASCADE, related_name="evidence_records")
    item_type = models.CharField(max_length=16, choices=ProposalItemType.choices)
    proposed_section = models.ForeignKey(ProposedSection, on_delete=models.CASCADE, null=True, blank=True, related_name="evidence_records")
    proposed_concept = models.ForeignKey(ProposedConcept, on_delete=models.CASCADE, null=True, blank=True, related_name="evidence_records")
    hierarchy_node = models.ForeignKey("content_processing.DocumentHierarchyNode", on_delete=models.PROTECT, related_name="proposal_evidence")
    semantic_segment = models.ForeignKey("content_processing.SemanticSegment", on_delete=models.PROTECT, null=True, blank=True, related_name="proposal_evidence")
    extracted_block = models.ForeignKey("content_processing.ExtractedBlock", on_delete=models.PROTECT, null=True, blank=True, related_name="proposal_evidence")
    source_page_start = models.PositiveIntegerField(null=True, blank=True)
    source_page_end = models.PositiveIntegerField(null=True, blank=True)
    evidence_strength = models.CharField(max_length=32)
    confidence = models.FloatField(default=0)
    reasoning_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_proposal_evidence"
        constraints = [
            models.UniqueConstraint(fields=["proposal", "item_type", "proposed_section", "proposed_concept", "semantic_segment", "extracted_block"], name="cp_proposal_evidence_unique"),
            models.CheckConstraint(condition=models.Q(confidence__gte=0) & models.Q(confidence__lte=1), name="cp_proposal_evidence_confidence_range"),
        ]

    def clean(self) -> None:
        if self.item_type == ProposalItemType.SECTION and (not self.proposed_section_id or self.proposed_concept_id):
            raise ValidationError("Section evidence must reference exactly one proposed section.")
        if self.item_type == ProposalItemType.CONCEPT and (not self.proposed_concept_id or not self.semantic_segment_id):
            raise ValidationError("Concept evidence requires a proposed concept and semantic segment.")
        if not 0 <= self.confidence <= 1:
            raise ValidationError("Proposal evidence confidence must be between zero and one.")


class ProposalValidation(models.Model):
    proposal = models.ForeignKey(AcademicImportProposal, on_delete=models.CASCADE, related_name="validations")
    code = models.CharField(max_length=128)
    severity = models.CharField(max_length=16)
    passed = models.BooleanField(default=True)
    public_message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_proposal_validation"


class ProposalDecision(models.Model):
    proposal = models.ForeignKey(AcademicImportProposal, on_delete=models.CASCADE, related_name="decisions")
    decision = models.CharField(max_length=32, choices=ProposalDecisionType.choices)
    decided_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="academic_import_decisions")
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_proposal_decision"
        ordering = ["created_at"]


class ProposalRevision(models.Model):
    proposal = models.ForeignKey(AcademicImportProposal, on_delete=models.CASCADE, related_name="revisions")
    revision_number = models.PositiveIntegerField()
    changed_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="academic_import_revisions")
    changes = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_proposal_revision"
        constraints = [models.UniqueConstraint(fields=["proposal", "revision_number"], name="cp_proposal_revision_unique")]


class AcademicPopulationJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(AcademicImportProposal, on_delete=models.PROTECT, related_name="population_jobs")
    job = models.ForeignKey("content_processing.ContentProcessingJob", on_delete=models.CASCADE, related_name="academic_population_jobs")
    attempt = models.ForeignKey("content_processing.ProcessingAttempt", on_delete=models.CASCADE, related_name="academic_population_jobs")
    population_version = models.CharField(max_length=64)
    academic_schema_version = models.CharField(max_length=64)
    status = models.CharField(max_length=32, choices=PopulationJobStatus.choices, default=PopulationJobStatus.READY_FOR_POPULATION)
    created_sections = models.PositiveIntegerField(default=0)
    updated_sections = models.PositiveIntegerField(default=0)
    created_concepts = models.PositiveIntegerField(default=0)
    updated_concepts = models.PositiveIntegerField(default=0)
    warnings = models.JSONField(default=list, blank=True)
    statistics = models.JSONField(default=dict, blank=True)
    failure_code = models.CharField(max_length=128, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_academic_population_job"
        constraints = [models.UniqueConstraint(fields=["proposal", "population_version", "academic_schema_version"], name="cp_population_identity_unique")]
