from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ReviewSessionStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not started"
    IN_PROGRESS = "in_progress", "In progress"
    READY_FOR_APPROVAL = "ready_for_approval", "Ready for approval"
    APPROVED = "approved", "Approved"
    APPROVED_WITH_EDITS = "approved_with_edits", "Approved with edits"
    REJECTED = "rejected", "Rejected"
    REPROCESS_REQUESTED = "reprocess_requested", "Reprocessing requested"
    SUPERSEDED = "superseded", "Superseded"
    ABANDONED = "abandoned", "Abandoned"


class ReviewItemType(models.TextChoices):
    SECTION = "section", "Section"
    CONCEPT = "concept", "Concept"


class ItemDecisionType(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    EDITED = "edited", "Edited"
    MOVED = "moved", "Moved"


class FindingResolutionType(models.TextChoices):
    REJECTION = "rejection", "Resolved by rejection"
    EDIT = "edit", "Resolved by edit"
    MOVE = "move", "Resolved by move"
    OVERRIDE = "override", "Resolved by override"


class ProposalReviewSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey("content_processing.AcademicImportProposal", on_delete=models.PROTECT, related_name="academic_review_sessions")
    proposal_version = models.CharField(max_length=64)
    proposal_checksum = models.CharField(max_length=128)
    status = models.CharField(max_length=32, choices=ReviewSessionStatus.choices, default=ReviewSessionStatus.NOT_STARTED)
    version = models.PositiveIntegerField(default=1)
    opened_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="opened_academic_reviews")
    reviewer = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="academic_reviews")
    submitted_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_review_session"
        ordering = ["-created_at"]

    def start(self, reviewer) -> None:
        if self.status != ReviewSessionStatus.NOT_STARTED:
            raise ValidationError("Only a review that has not started may be opened.")
        self.reviewer = reviewer
        self.status = ReviewSessionStatus.IN_PROGRESS
        self.version += 1

    def submit(self) -> None:
        if self.status != ReviewSessionStatus.IN_PROGRESS:
            raise ValidationError("Only an in-progress review may be submitted.")
        self.status = ReviewSessionStatus.READY_FOR_APPROVAL
        self.submitted_at = timezone.now()
        self.version += 1

    def approve(self, *, with_edits: bool) -> None:
        if self.status != ReviewSessionStatus.READY_FOR_APPROVAL:
            raise ValidationError("Only a review ready for approval may be approved.")
        self.status = ReviewSessionStatus.APPROVED_WITH_EDITS if with_edits else ReviewSessionStatus.APPROVED
        self.closed_at = timezone.now()
        self.version += 1

    def reject(self) -> None:
        if self.status not in {ReviewSessionStatus.IN_PROGRESS, ReviewSessionStatus.READY_FOR_APPROVAL}:
            raise ValidationError("Only an active review may be rejected.")
        self.status = ReviewSessionStatus.REJECTED
        self.closed_at = timezone.now()
        self.version += 1

    def request_reprocessing(self) -> None:
        if self.status not in {ReviewSessionStatus.IN_PROGRESS, ReviewSessionStatus.READY_FOR_APPROVAL}:
            raise ValidationError("Only an active review may request reprocessing.")
        self.status = ReviewSessionStatus.REPROCESS_REQUESTED
        self.closed_at = timezone.now()
        self.version += 1


class ProposalItemDecision(models.Model):
    session = models.ForeignKey(ProposalReviewSession, on_delete=models.CASCADE, related_name="item_decisions")
    item_type = models.CharField(max_length=16, choices=ReviewItemType.choices)
    proposed_section = models.ForeignKey("content_processing.ProposedSection", on_delete=models.PROTECT, null=True, blank=True, related_name="review_decisions")
    proposed_concept = models.ForeignKey("content_processing.ProposedConcept", on_delete=models.PROTECT, null=True, blank=True, related_name="review_decisions")
    decision = models.CharField(max_length=16, choices=ItemDecisionType.choices, default=ItemDecisionType.PENDING)
    decided_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="academic_item_decisions")
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_review_item_decision"
        constraints = [models.UniqueConstraint(fields=["session", "item_type", "proposed_section", "proposed_concept"], name="ar_item_decision_unique")]

    @property
    def item_id(self):
        return self.proposed_section_id or self.proposed_concept_id

    def clean(self):
        if self.item_type == ReviewItemType.SECTION and (not self.proposed_section_id or self.proposed_concept_id):
            raise ValidationError("Section decisions must reference exactly one proposed section.")
        if self.item_type == ReviewItemType.CONCEPT and (not self.proposed_concept_id or self.proposed_section_id):
            raise ValidationError("Concept decisions must reference exactly one proposed concept.")


class ProposalItemEdit(models.Model):
    decision = models.OneToOneField(ProposalItemDecision, on_delete=models.CASCADE, related_name="edit")
    title = models.CharField(max_length=255, blank=True)
    ordering = models.PositiveIntegerField(null=True, blank=True)
    parent_section = models.ForeignKey("content_processing.ProposedSection", on_delete=models.PROTECT, null=True, blank=True, related_name="review_parent_edits")
    target_section = models.ForeignKey("content_processing.ProposedSection", on_delete=models.PROTECT, null=True, blank=True, related_name="review_concept_moves")
    edited_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="academic_item_edits")
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_review_item_edit"


class ProposalBulkDecision(models.Model):
    session = models.ForeignKey(ProposalReviewSession, on_delete=models.CASCADE, related_name="bulk_decisions")
    policy_code = models.CharField(max_length=64)
    policy_version = models.CharField(max_length=64)
    affected_count = models.PositiveIntegerField()
    preview = models.JSONField(default=dict)
    applied_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="academic_bulk_decisions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "academic_review_bulk_decision"


class ProposalOverride(models.Model):
    session = models.ForeignKey(ProposalReviewSession, on_delete=models.CASCADE, related_name="overrides")
    validation = models.ForeignKey("content_processing.ProposalValidation", on_delete=models.PROTECT, related_name="academic_review_overrides")
    overridden_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="academic_review_overrides")
    reason = models.TextField()
    policy_version = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "academic_review_override"
        constraints = [models.UniqueConstraint(fields=["session", "validation"], name="ar_override_unique")]


class ProposalFindingResolution(models.Model):
    session = models.ForeignKey(ProposalReviewSession, on_delete=models.CASCADE, related_name="finding_resolutions")
    validation = models.ForeignKey("content_processing.ProposalValidation", on_delete=models.PROTECT, related_name="academic_review_resolutions")
    resolution_type = models.CharField(max_length=16, choices=FindingResolutionType.choices)
    item_decision = models.ForeignKey(ProposalItemDecision, on_delete=models.PROTECT, null=True, blank=True, related_name="finding_resolutions")
    override = models.OneToOneField(ProposalOverride, on_delete=models.PROTECT, null=True, blank=True, related_name="resolution")
    resolved_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="academic_finding_resolutions")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "academic_review_finding_resolution"
        constraints = [models.UniqueConstraint(fields=["session", "validation"], name="ar_finding_resolution_unique")]


class ApprovalProjectionStatus(models.TextChoices):
    CREATED = "created", "Created"
    READY_FOR_POPULATION = "ready_for_population", "Ready for population"
    POPULATING = "populating", "Populating"
    SUPERSEDED = "superseded", "Superseded"
    POPULATED = "populated", "Populated"


class ApprovalReadinessSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProposalReviewSession, on_delete=models.PROTECT, related_name="readiness_snapshots")
    proposal = models.ForeignKey("content_processing.AcademicImportProposal", on_delete=models.PROTECT, related_name="approval_readiness_snapshots")
    proposal_version = models.CharField(max_length=64)
    proposal_checksum = models.CharField(max_length=128)
    review_session_version = models.PositiveIntegerField()
    ready = models.BooleanField(default=False)
    pending_sections = models.PositiveIntegerField(default=0)
    pending_concepts = models.PositiveIntegerField(default=0)
    accepted_sections = models.PositiveIntegerField(default=0)
    accepted_concepts = models.PositiveIntegerField(default=0)
    rejected_sections = models.PositiveIntegerField(default=0)
    rejected_concepts = models.PositiveIntegerField(default=0)
    blocking_findings = models.PositiveIntegerField(default=0)
    resolved_findings = models.PositiveIntegerField(default=0)
    orphan_concepts = models.PositiveIntegerField(default=0)
    invalid_hierarchy = models.PositiveIntegerField(default=0)
    duplicate_titles = models.PositiveIntegerField(default=0)
    override_count = models.PositiveIntegerField(default=0)
    policy_version = models.CharField(max_length=64)
    reasons = models.JSONField(default=list)
    checksum = models.CharField(max_length=128)
    evaluated_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="academic_readiness_evaluations")
    evaluated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "academic_review_readiness_snapshot"
        ordering = ["-evaluated_at"]
        constraints = [models.UniqueConstraint(fields=["session", "review_session_version", "checksum"], name="ar_readiness_snapshot_unique")]


class ApprovalDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProposalReviewSession, on_delete=models.PROTECT, related_name="approval_decisions")
    proposal = models.ForeignKey("content_processing.AcademicImportProposal", on_delete=models.PROTECT, related_name="review_approval_decisions")
    readiness_snapshot = models.ForeignKey(ApprovalReadinessSnapshot, on_delete=models.PROTECT, related_name="approval_decisions")
    decision = models.CharField(max_length=32, choices=[("approved", "Approved"), ("approved_with_edits", "Approved with edits"), ("rejected", "Rejected")])
    approval_version = models.CharField(max_length=128)
    idempotency_key = models.CharField(max_length=128)
    reason = models.TextField(blank=True)
    decided_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="review_approval_decisions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "academic_review_approval_decision"
        constraints = [
            models.UniqueConstraint(fields=["session", "idempotency_key"], name="ar_approval_idempotency_unique"),
            models.UniqueConstraint(fields=["session", "approval_version"], name="ar_approval_version_unique"),
        ]


class ApprovedProposalProjection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(ProposalReviewSession, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_projection")
    approval_decision = models.OneToOneField(ApprovalDecision, on_delete=models.PROTECT, null=True, blank=True, related_name="projection")
    proposal = models.ForeignKey("content_processing.AcademicImportProposal", on_delete=models.PROTECT, related_name="approved_review_projections")
    proposal_checksum = models.CharField(max_length=128)
    approval_version = models.CharField(max_length=128)
    projection_version = models.CharField(max_length=64)
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, null=True, blank=True, related_name="approved_proposal_projections")
    subject = models.ForeignKey("academic.Subject", on_delete=models.PROTECT, null=True, blank=True, related_name="approved_proposal_projections")
    institution = models.ForeignKey("users.Institution", on_delete=models.PROTECT, null=True, blank=True, related_name="approved_proposal_projections")
    status = models.CharField(max_length=32, choices=ApprovalProjectionStatus.choices, default=ApprovalProjectionStatus.CREATED)
    approved_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="approved_academic_projections")
    checksum = models.CharField(max_length=128)
    hierarchy_checksum = models.CharField(max_length=128, blank=True)
    concepts_checksum = models.CharField(max_length=128, blank=True)
    provenance_checksum = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "academic_review_approved_projection"
        constraints = [models.UniqueConstraint(fields=["proposal", "approval_version"], name="ar_projection_approval_version_unique")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Approved proposal projections are immutable.")
        super().save(*args, **kwargs)


class ApprovedSection(models.Model):
    projection = models.ForeignKey(ApprovedProposalProjection, on_delete=models.CASCADE, related_name="sections")
    source = models.ForeignKey("content_processing.ProposedSection", on_delete=models.PROTECT, related_name="approved_projection_items")
    title = models.CharField(max_length=255)
    canonical_title = models.CharField(max_length=255, default="")
    ordering = models.PositiveIntegerField()
    depth = models.PositiveIntegerField(default=1)
    parent_source = models.ForeignKey("content_processing.ProposedSection", on_delete=models.PROTECT, null=True, blank=True, related_name="approved_child_projection_items")
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children")
    page_range = models.JSONField(default=dict)
    evidence_references = models.JSONField(default=list)
    review_decision = models.ForeignKey(ProposalItemDecision, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_section_projections")
    edit_reference = models.ForeignKey(ProposalItemEdit, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_section_projections")
    override_references = models.JSONField(default=list)

    class Meta:
        db_table = "academic_review_approved_section"
        ordering = ["ordering"]
        constraints = [models.UniqueConstraint(fields=["projection", "ordering"], name="ar_approved_section_order_unique")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Approved section projections are immutable.")
        super().save(*args, **kwargs)


class ApprovedConcept(models.Model):
    projection = models.ForeignKey(ApprovedProposalProjection, on_delete=models.CASCADE, related_name="concepts")
    source = models.ForeignKey("content_processing.ProposedConcept", on_delete=models.PROTECT, related_name="approved_projection_items")
    section = models.ForeignKey(ApprovedSection, on_delete=models.CASCADE, related_name="concepts")
    title = models.CharField(max_length=255)
    canonical_title = models.CharField(max_length=255, default="")
    ordering = models.PositiveIntegerField()
    supporting_text = models.TextField()
    explanation = models.TextField()
    page_range = models.JSONField(default=dict)
    supporting_evidence = models.JSONField(default=list)
    review_decision = models.ForeignKey(ProposalItemDecision, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_concept_projections")
    edit_reference = models.ForeignKey(ProposalItemEdit, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_concept_projections")
    override_references = models.JSONField(default=list)

    class Meta:
        db_table = "academic_review_approved_concept"
        ordering = ["section_id", "ordering"]
        constraints = [models.UniqueConstraint(fields=["section", "ordering"], name="ar_approved_concept_order_unique")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Approved concept projections are immutable.")
        super().save(*args, **kwargs)


class PopulationRunStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    POPULATING = "populating", "Populating"
    POPULATED = "populated", "Populated"
    FAILED = "failed", "Failed"


class PopulationOutcome(models.TextChoices):
    CREATED = "created", "Created"
    MATCHED = "matched", "Matched"


class AcademicPopulationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    approved_projection = models.ForeignKey(ApprovedProposalProjection, on_delete=models.PROTECT, related_name="population_runs")
    approval_decision = models.ForeignKey(ApprovalDecision, on_delete=models.PROTECT, related_name="population_runs")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, related_name="academic_population_runs")
    subject = models.ForeignKey("academic.Subject", on_delete=models.PROTECT, related_name="academic_population_runs")
    requested_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="academic_population_runs")
    idempotency_key = models.CharField(max_length=128, unique=True)
    request_fingerprint = models.CharField(max_length=128)
    projection_fingerprint = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=PopulationRunStatus.choices, default=PopulationRunStatus.PLANNED)
    prior_run = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="retries")
    plan_snapshot = models.JSONField(default=dict)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=64, blank=True)
    failure_message = models.CharField(max_length=500, blank=True)
    created_section_count = models.PositiveIntegerField(default=0)
    matched_section_count = models.PositiveIntegerField(default=0)
    created_concept_count = models.PositiveIntegerField(default=0)
    matched_concept_count = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_review_population_run"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["approved_projection"], condition=models.Q(status=PopulationRunStatus.POPULATED), name="ar_one_populated_run_per_projection"),
        ]
        indexes = [
            models.Index(fields=["approved_projection", "status"], name="ar_pop_projection_status"),
            models.Index(fields=["resource", "subject"], name="ar_pop_resource_subject"),
            models.Index(fields=["requested_by", "created_at"], name="ar_pop_actor_created"),
        ]

    def start(self):
        if self.status != PopulationRunStatus.PLANNED:
            raise ValidationError("Only a planned population run may start.")
        self.status = PopulationRunStatus.POPULATING
        self.started_at = timezone.now()
        self.version += 1

    def complete(self, *, created_sections, matched_sections, created_concepts, matched_concepts):
        if self.status != PopulationRunStatus.POPULATING:
            raise ValidationError("Only a populating run may complete.")
        expected_sections = self.plan_snapshot.get("expected_section_count", 0)
        expected_concepts = self.plan_snapshot.get("expected_concept_count", 0)
        if created_sections + matched_sections != expected_sections or created_concepts + matched_concepts != expected_concepts:
            raise ValidationError("Population result does not reconcile with the immutable plan.")
        self.created_section_count, self.matched_section_count = created_sections, matched_sections
        self.created_concept_count, self.matched_concept_count = created_concepts, matched_concepts
        self.status = PopulationRunStatus.POPULATED
        self.completed_at = timezone.now()
        self.version += 1

    def fail(self, *, code, message=""):
        if self.status == PopulationRunStatus.POPULATED:
            raise ValidationError("A populated run is terminal.")
        if not (code or "").strip():
            raise ValidationError("A stable failure code is required.")
        self.status, self.failure_code, self.failure_message = PopulationRunStatus.FAILED, code, message
        self.failed_at = timezone.now()
        self.version += 1


class SectionPopulationMapping(models.Model):
    population_run = models.ForeignKey(AcademicPopulationRun, on_delete=models.PROTECT, related_name="section_mappings")
    approved_section = models.ForeignKey(ApprovedSection, on_delete=models.PROTECT, related_name="population_mappings")
    academic_section_id = models.UUIDField()
    stable_source_key = models.CharField(max_length=160)
    outcome = models.CharField(max_length=16, choices=PopulationOutcome.choices)
    sequence_number = models.PositiveIntegerField()
    populated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "academic_review_section_population_mapping"
        constraints = [
            models.UniqueConstraint(fields=["population_run", "approved_section"], name="ar_pop_section_item_unique"),
            models.UniqueConstraint(fields=["population_run", "stable_source_key"], name="ar_pop_section_key_unique"),
        ]
        indexes = [models.Index(fields=["approved_section", "academic_section_id"], name="ar_pop_section_provenance")]


class ConceptPopulationMapping(models.Model):
    population_run = models.ForeignKey(AcademicPopulationRun, on_delete=models.PROTECT, related_name="concept_mappings")
    approved_concept = models.ForeignKey(ApprovedConcept, on_delete=models.PROTECT, related_name="population_mappings")
    academic_concept_id = models.UUIDField()
    academic_section_id = models.UUIDField()
    stable_source_key = models.CharField(max_length=160)
    outcome = models.CharField(max_length=16, choices=PopulationOutcome.choices)
    sequence_number = models.PositiveIntegerField()
    populated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "academic_review_concept_population_mapping"
        constraints = [
            models.UniqueConstraint(fields=["population_run", "approved_concept"], name="ar_pop_concept_item_unique"),
            models.UniqueConstraint(fields=["population_run", "stable_source_key"], name="ar_pop_concept_key_unique"),
        ]
        indexes = [models.Index(fields=["approved_concept", "academic_concept_id"], name="ar_pop_concept_provenance")]


@dataclass(frozen=True)
class ProposalReviewSummary:
    section_accepted: int
    section_rejected: int
    section_pending: int
    concept_accepted: int
    concept_rejected: int
    concept_pending: int
    blocking_findings: int
    resolved_findings: int
    outstanding_findings: int
    overrides: int
    ready: bool
