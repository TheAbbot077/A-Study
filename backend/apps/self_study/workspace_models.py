from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class SelfStudyWorkspaceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    INTENT_REQUIRED = "INTENT_REQUIRED", "Intent required"
    INTENT_IN_PROGRESS = "INTENT_IN_PROGRESS", "Intent in progress"
    MATERIALS_REQUIRED = "MATERIALS_REQUIRED", "Materials required"
    MATERIALS_PROCESSING = "MATERIALS_PROCESSING", "Materials processing"
    MATERIALS_BLOCKED = "MATERIALS_BLOCKED", "Materials blocked"
    MATERIALS_READY = "MATERIALS_READY", "Materials ready"
    DIAGNOSTIC_READY = "DIAGNOSTIC_READY", "Diagnostic ready"
    DIAGNOSTIC_IN_PROGRESS = "DIAGNOSTIC_IN_PROGRESS", "Diagnostic in progress"
    DIAGNOSTIC_COMPLETE = "DIAGNOSTIC_COMPLETE", "Diagnostic complete"
    PLANNING_REQUIRED = "PLANNING_REQUIRED", "Planning required"
    PLANNING_IN_PROGRESS = "PLANNING_IN_PROGRESS", "Planning in progress"
    PLAN_READY = "PLAN_READY", "Plan ready"
    PREPARATION_IN_PROGRESS = "PREPARATION_IN_PROGRESS", "Preparation in progress"
    READY_TO_LEARN = "READY_TO_LEARN", "Ready to learn"
    LEARNING_ACTIVE = "LEARNING_ACTIVE", "Learning active"
    BLOCKED = "BLOCKED", "Blocked"
    STALE = "STALE", "Stale"
    ARCHIVED = "ARCHIVED", "Archived"


class WorkspaceMaterialStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "Uploaded"
    PROCESSING = "PROCESSING", "Processing"
    PROCESSED = "PROCESSED", "Processed"
    EXTRACTION_FAILED = "EXTRACTION_FAILED", "Extraction failed"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT", "Unsupported format"
    UNLICENSED = "UNLICENSED", "Unlicensed"
    UNSAFE = "UNSAFE", "Unsafe"
    QUARANTINED = "QUARANTINED", "Quarantined"
    RETIRED = "RETIRED", "Retired"
    STALE = "STALE", "Stale"
    ELIGIBLE = "ELIGIBLE", "Eligible"
    INELIGIBLE = "INELIGIBLE", "Ineligible"


class SelfStudyWorkspace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="self_study_workspaces")
    learner = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="self_study_workspaces")
    display_name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=SelfStudyWorkspaceStatus.choices,
        default=SelfStudyWorkspaceStatus.INTENT_REQUIRED,
    )
    intent = models.ForeignKey(
        "self_study.SelfStudyIntent",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workspaces",
    )
    curriculum_resolution = models.ForeignKey(
        "self_study.CurriculumResolutionAttempt",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workspaces",
    )
    published_graph = models.ForeignKey(
        "self_study.CurriculumGraphVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workspaces",
    )
    active_diagnostic = models.ForeignKey(
        "self_study.EntryDiagnostic",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="active_for_workspaces",
    )
    latest_coverage_evaluation = models.ForeignKey(
        "self_study.CurriculumCoverageEvaluation",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workspaces",
    )
    active_bridge_plan = models.ForeignKey(
        "self_study.BridgePlan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workspaces",
    )
    active_teaching_preparation = models.ForeignKey(
        "self_study.TeachingPreparationManifest",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workspaces",
    )
    active_teaching_session = models.ForeignKey(
        "self_study.SelfStudyTeachingSession",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workspaces",
    )
    idempotency_key = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "self_study_workspace"
        ordering = ["-updated_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "tenant", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="ssi_ws_idem_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["learner", "status"], name="ssi_ws_learner_idx"),
            models.Index(fields=["tenant", "status"], name="ssi_ws_tenant_idx"),
            models.Index(fields=["intent"], name="ssi_ws_intent_idx"),
        ]

    def archive(self, *, when):
        if self.status == SelfStudyWorkspaceStatus.ARCHIVED:
            return False
        self.status = SelfStudyWorkspaceStatus.ARCHIVED
        self.archived_at = when
        self.version += 1
        return True


class SelfStudyWorkspaceMaterial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(SelfStudyWorkspace, on_delete=models.PROTECT, related_name="materials")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, related_name="self_study_workspace_links")
    content_processing_job = models.ForeignKey(
        "content_processing.ContentProcessingJob",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="self_study_workspace_links",
    )
    status = models.CharField(
        max_length=32,
        choices=WorkspaceMaterialStatus.choices,
        default=WorkspaceMaterialStatus.UPLOADED,
    )
    blocker_codes = models.JSONField(default=list, blank=True)
    safe_status_summary = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True)
    attached_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="attached_self_study_materials")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "self_study_workspace_material"
        ordering = ["created_at", "resource_id"]
        constraints = [
            models.UniqueConstraint(fields=["workspace", "resource"], name="ssi_wsm_resource_unique"),
            models.UniqueConstraint(
                fields=["workspace", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="ssi_wsm_idem_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["workspace", "status"], name="ssi_wsm_status_idx"),
            models.Index(fields=["resource"], name="ssi_wsm_resource_idx"),
        ]
