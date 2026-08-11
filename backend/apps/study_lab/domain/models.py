"""
Study Lab domain models.

Study Lab is a composition, orchestration, and workspace projection layer.
It does NOT own curriculum, teaching, retrieval, evidence, or mastery.
It references authoritative bounded contexts by identifier only.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .enums import (
    ArtefactTransformationRequestStatus,
    ActivityType,
    InvocationStatus,
    NextActionKey,
    NoteStatus,
    PanelKey,
    ProviderContext,
    InstrumentFamily,
    ResumeOutcome,
    SnapshotStatus,
    StudyArtefactCompatibilityStatus,
    StudyArtefactLifecycle,
    StudyArtefactLineageRelation,
    StudyArtefactOrigin,
    StudyArtefactType,
    StudyArtefactVisibility,
    StudyToolManifestStatus,
    StudyScaffoldGenerationStatus,
    StudyScaffoldGenerationType,
    ToolAvailabilityReasonCode,
    ToolCategory,
    ToolKey,
    ToolStatus,
    ToolInvocationLifecycleStatus,
    WorkspaceStatus,
    WorkspaceToolSessionStatus,
    WorkspaceType,
)
from .policies import WorkspaceLifecyclePolicy


# ============================================================================
# StudyWorkspace
# ============================================================================

class StudyWorkspace(models.Model):
    """The learner's owned place of study.

    One coherent workspace per learner context. Institutions never own
    learner workspaces.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="study_lab_workspaces",
    )
    tenant = models.ForeignKey(
        "users.Institution",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="study_lab_workspaces",
    )
    workspace_type = models.CharField(
        max_length=32,
        choices=WorkspaceType.choices,
        default=WorkspaceType.SELF_STUDY,
    )
    status = models.CharField(
        max_length=24,
        choices=WorkspaceStatus.choices,
        default=WorkspaceStatus.DRAFT,
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    active_context = models.ForeignKey(
        "study_lab.WorkspaceContext",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_study_lab_workspaces",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "study_lab_workspace"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["learner", "status"], name="sl_ws_learner_status_idx"),
            models.Index(fields=["tenant", "status"], name="sl_ws_tenant_status_idx"),
            models.Index(fields=["workspace_type", "status"], name="sl_ws_type_status_idx"),
            models.Index(fields=["last_opened_at"], name="sl_ws_last_opened_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(workspace_type=WorkspaceType.SELF_STUDY, tenant__isnull=True)
                | Q(workspace_type=WorkspaceType.PERSONAL_REVIEW, tenant__isnull=True)
                | Q(workspace_type=WorkspaceType.INSTITUTIONAL, tenant__isnull=False)
                | Q(workspace_type=WorkspaceType.HYBRID, tenant__isnull=False),
                name="sl_ws_tenant_required_by_type",
            ),
            models.CheckConstraint(
                condition=Q(status__in=WorkspaceStatus.values),
                name="sl_ws_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(workspace_type__in=WorkspaceType.values),
                name="sl_ws_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Workspace {self.id} ({self.workspace_type}) for {self.learner_id}"

    def clean(self):
        super().clean()
        if self.workspace_type in {WorkspaceType.SELF_STUDY, WorkspaceType.PERSONAL_REVIEW}:
            if self.tenant_id is not None:
                raise ValidationError(
                    "Self-study and personal-review workspaces must not have a tenant.",
                    code="WORKSPACE_TENANT_NOT_ALLOWED",
                )
        if self.workspace_type in {WorkspaceType.INSTITUTIONAL, WorkspaceType.HYBRID}:
            if self.tenant_id is None:
                raise ValidationError(
                    "Institutional and hybrid workspaces require a tenant.",
                    code="WORKSPACE_TENANT_REQUIRED",
                )
        if self.status == WorkspaceStatus.ACTIVE and not self.activated_at:
            raise ValidationError("Active workspaces must record activated_at.", code="WORKSPACE_ACTIVATED_AT_REQUIRED")
        if self.status == WorkspaceStatus.ARCHIVED and not self.archived_at:
            raise ValidationError("Archived workspaces must record archived_at.", code="WORKSPACE_ARCHIVED_AT_REQUIRED")

    def transition_to(self, status: str, *, when=None) -> bool:
        """Transition workspace to a new status. Returns True if changed."""
        if self.status == status:
            return False
        WorkspaceLifecyclePolicy.validate(self.status, status)
        when = when or timezone.now()
        previous = self.status
        self.status = status
        self.version += 1

        if status == WorkspaceStatus.ACTIVE and not self.activated_at:
            self.activated_at = when
        if status == WorkspaceStatus.PAUSED and not self.paused_at:
            self.paused_at = when
        if status == WorkspaceStatus.COMPLETED and not self.completed_at:
            self.completed_at = when
        if status == WorkspaceStatus.SUSPENDED and not self.suspended_at:
            self.suspended_at = when
        if status == WorkspaceStatus.ARCHIVED and not self.archived_at:
            self.archived_at = when

        return True

    def activate(self, *, when=None) -> bool:
        return self.transition_to(WorkspaceStatus.ACTIVE, when=when)

    def pause(self, *, when=None) -> bool:
        return self.transition_to(WorkspaceStatus.PAUSED, when=when)

    def resume(self, *, when=None) -> bool:
        return self.transition_to(WorkspaceStatus.ACTIVE, when=when)

    def suspend(self, *, when=None) -> bool:
        return self.transition_to(WorkspaceStatus.SUSPENDED, when=when)

    def complete(self, *, when=None) -> bool:
        return self.transition_to(WorkspaceStatus.COMPLETED, when=when)

    def archive(self, *, when=None) -> bool:
        return self.transition_to(WorkspaceStatus.ARCHIVED, when=when)

    def reopen(self, *, when=None) -> bool:
        """Reopen a completed workspace to ACTIVE."""
        if self.status != WorkspaceStatus.COMPLETED:
            raise ValidationError(
                "Only completed workspaces can be reopened.",
                code="WORKSPACE_NOT_COMPLETED",
            )
        if not WorkspaceLifecyclePolicy.can_reopen_completed():
            raise ValidationError(
                "Policy does not allow reopening completed workspaces.",
                code="WORKSPACE_REOPEN_NOT_ALLOWED",
            )
        return self.transition_to(WorkspaceStatus.ACTIVE, when=when)

    def mark_opened(self, *, when=None) -> None:
        self.last_opened_at = when or timezone.now()

    @property
    def is_active(self) -> bool:
        return self.status == WorkspaceStatus.ACTIVE

    @property
    def is_archived(self) -> bool:
        return self.status == WorkspaceStatus.ARCHIVED

    @property
    def is_suspended(self) -> bool:
        return self.status == WorkspaceStatus.SUSPENDED

    @property
    def is_mutable(self) -> bool:
        return WorkspaceLifecyclePolicy.is_mutable(self.status)


# ============================================================================
# WorkspaceContext
# ============================================================================

class WorkspaceContext(models.Model):
    """Durable study context referencing authoritative bounded contexts by ID.

    These are references, not authorities. Study Lab never duplicates
    the authoritative entities.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(
        StudyWorkspace,
        on_delete=models.CASCADE,
        related_name="context",
    )
    active_learning_journey_id = models.UUIDField(null=True, blank=True)
    active_institutional_journey_id = models.UUIDField(null=True, blank=True)
    active_subject_id = models.UUIDField(null=True, blank=True)
    active_course_id = models.UUIDField(null=True, blank=True)
    active_programme_id = models.UUIDField(null=True, blank=True)
    active_curriculum_reference_id = models.UUIDField(null=True, blank=True)
    active_competency_id = models.UUIDField(null=True, blank=True)
    active_concept_id = models.UUIDField(null=True, blank=True)
    active_abbot_session_id = models.UUIDField(null=True, blank=True)
    active_ariel_session_id = models.UUIDField(null=True, blank=True)
    active_whiteboard_session_id = models.UUIDField(null=True, blank=True)
    active_concept_check_id = models.UUIDField(null=True, blank=True)
    source_versions = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "study_lab_workspace_context"

    def __str__(self) -> str:
        return f"Context for workspace {self.workspace_id}"

    def clean(self):
        super().clean()
        if self.active_learning_journey_id and self.active_institutional_journey_id:
            if self.active_learning_journey_id == self.active_institutional_journey_id:
                raise ValidationError(
                    "Learning journey and institutional journey cannot be the same reference.",
                    code="CONTEXT_JOURNEY_DUPLICATE",
                )

    def update_version(self) -> None:
        self.version += 1


# ============================================================================
# WorkspaceResumeState
# ============================================================================

class WorkspaceResumeState(models.Model):
    """Learner-safe continuation point for a workspace.

    Never stores hidden reasoning, raw prompts, answer keys, or
    retrieval internals.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(
        StudyWorkspace,
        on_delete=models.CASCADE,
        related_name="resume_state",
    )
    last_panel_key = models.CharField(max_length=32, choices=PanelKey.choices)
    last_tool_key = models.CharField(max_length=32, choices=ToolKey.choices, null=True, blank=True)
    last_activity_type = models.CharField(max_length=48, choices=ActivityType.choices)
    last_subject_id = models.UUIDField(null=True, blank=True)
    last_concept_id = models.UUIDField(null=True, blank=True)
    last_session_reference = models.CharField(max_length=128, blank=True)
    unfinished_activity_reference = models.CharField(max_length=128, blank=True)
    whiteboard_reference = models.CharField(max_length=128, blank=True)
    next_action_key = models.CharField(max_length=48, choices=NextActionKey.choices, default=NextActionKey.NO_RECOMMENDATION)
    next_action_reference = models.CharField(max_length=128, blank=True)
    resume_reason = models.CharField(max_length=64, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "study_lab_resume_state"

    def __str__(self) -> str:
        return f"Resume state for workspace {self.workspace_id}"

    def update_version(self) -> None:
        self.version += 1


# ============================================================================
# WorkspacePanelDefinition
# ============================================================================

class WorkspacePanelDefinition(models.Model):
    """Governed panel definitions for the workspace surface."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    panel_key = models.CharField(max_length=32, choices=PanelKey.choices, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    provider_context = models.CharField(max_length=32, choices=ProviderContext.choices)
    required_capability = models.CharField(max_length=64, blank=True)
    supported_workspace_types = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=ToolStatus.choices, default=ToolStatus.ACTIVE)
    sort_order = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "study_lab_panel_definition"
        ordering = ["sort_order", "panel_key"]

    def __str__(self) -> str:
        return f"Panel {self.panel_key} ({self.display_name})"

    @property
    def is_active(self) -> bool:
        return self.status == ToolStatus.ACTIVE

    def supports_workspace_type(self, workspace_type: str) -> bool:
        types = self.supported_workspace_types or []
        return workspace_type in types or not types


# ============================================================================
# StudyToolDefinition
# ============================================================================

class StudyToolDefinition(models.Model):
    """First-class tool registry for the Study Lab."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tool_key = models.CharField(max_length=32, choices=ToolKey.choices, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=32, choices=ToolCategory.choices)
    provider_context = models.CharField(max_length=32, choices=ProviderContext.choices)
    instrument_family = models.CharField(max_length=48, choices=InstrumentFamily.choices, default=InstrumentFamily.GENERAL_THINKING)
    required_capability = models.CharField(max_length=64, blank=True)
    input_artefact_types = models.JSONField(default=list, blank=True)
    output_artefact_types = models.JSONField(default=list, blank=True)
    supported_workspace_types = models.JSONField(default=list, blank=True)
    schema_versions = models.JSONField(default=list, blank=True)
    policy_key = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=24, choices=ToolStatus.choices, default=ToolStatus.ACTIVE)
    version = models.PositiveIntegerField(default=1)
    supports_transform = models.BooleanField(default=False)
    supports_import = models.BooleanField(default=False)
    supports_export = models.BooleanField(default=False)
    requires_runtime = models.BooleanField(default=False)
    runtime_provider = models.CharField(max_length=32, choices=ProviderContext.choices, blank=True, default="")
    offline_capable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "study_lab_tool_definition"
        ordering = ["tool_key"]

    def __str__(self) -> str:
        return f"Tool {self.tool_key} ({self.display_name})"

    @property
    def is_active(self) -> bool:
        return self.status == ToolStatus.ACTIVE

    @property
    def is_retired(self) -> bool:
        return self.status == ToolStatus.RETIRED

    def supports_workspace_type(self, workspace_type: str) -> bool:
        types = self.supported_workspace_types or []
        return workspace_type in types or not types


# ============================================================================
# WorkspaceToolAvailability
# ============================================================================

class WorkspaceToolAvailability(models.Model):
    """Deterministic, persisted tool availability for a workspace."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        StudyWorkspace,
        on_delete=models.CASCADE,
        related_name="tool_availabilities",
    )
    tool_definition = models.ForeignKey(
        StudyToolDefinition,
        on_delete=models.PROTECT,
        related_name="workspace_availabilities",
    )
    available = models.BooleanField(default=False)
    reason_code = models.CharField(
        max_length=48,
        choices=ToolAvailabilityReasonCode.choices,
        default=ToolAvailabilityReasonCode.AVAILABLE,
    )
    reason_detail = models.CharField(max_length=280, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)
    source_versions = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "study_lab_tool_availability"
        ordering = ["workspace", "tool_definition"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "tool_definition"],
                name="sl_ta_unique_workspace_tool",
            ),
        ]

    def __str__(self) -> str:
        return f"Availability for {self.tool_definition.tool_key} in workspace {self.workspace_id}"


# ============================================================================
# WorkspaceToolInvocation
# ============================================================================

class WorkspaceToolInvocation(models.Model):
    """Operational record of a tool invocation. Not evidence of learning."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        StudyWorkspace,
        on_delete=models.CASCADE,
        related_name="tool_invocations",
    )
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="study_lab_tool_invocations",
    )
    tool_definition = models.ForeignKey(
        StudyToolDefinition,
        on_delete=models.PROTECT,
        related_name="invocations",
    )
    provider_context = models.CharField(max_length=32, choices=ProviderContext.choices)
    provider_reference = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=24,
        choices=ToolInvocationLifecycleStatus.choices,
        default=ToolInvocationLifecycleStatus.REQUESTED,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    reason_code = models.CharField(max_length=48, blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "study_lab_tool_invocation"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["workspace", "requested_at"], name="sl_inv_ws_time_idx"),
            models.Index(fields=["learner", "requested_at"], name="sl_inv_learner_time_idx"),
            models.Index(fields=["tool_definition", "status"], name="sl_inv_tool_status_idx"),
            models.Index(fields=["idempotency_key"], name="sl_inv_idem_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="sl_inv_unique_idem",
            ),
        ]

    def __str__(self) -> str:
        return f"Invocation {self.id} ({self.tool_definition.tool_key}) status={self.status}"

    def mark_validated(self, *, when=None) -> bool:
        if self.status != ToolInvocationLifecycleStatus.REQUESTED:
            return False
        self.status = ToolInvocationLifecycleStatus.VALIDATED
        self.started_at = when or timezone.now()
        return True

    def mark_dispatched(self, *, when=None) -> bool:
        if self.status not in {ToolInvocationLifecycleStatus.REQUESTED, ToolInvocationLifecycleStatus.VALIDATED}:
            return False
        self.status = ToolInvocationLifecycleStatus.DISPATCHED
        self.started_at = when or timezone.now()
        return True

    def mark_running(self, *, when=None) -> bool:
        if self.status not in {ToolInvocationLifecycleStatus.VALIDATED, ToolInvocationLifecycleStatus.DISPATCHED}:
            return False
        self.status = ToolInvocationLifecycleStatus.RUNNING
        self.started_at = self.started_at or when or timezone.now()
        return True

    def mark_completed(self, *, when=None) -> bool:
        if self.status not in {ToolInvocationLifecycleStatus.REQUESTED, ToolInvocationLifecycleStatus.VALIDATED, ToolInvocationLifecycleStatus.DISPATCHED, ToolInvocationLifecycleStatus.RUNNING}:
            return False
        self.status = ToolInvocationLifecycleStatus.COMPLETED
        self.completed_at = when or timezone.now()
        return True

    def mark_rejected(self, *, reason_code: str = "", when=None) -> bool:
        if self.status in {ToolInvocationLifecycleStatus.COMPLETED, ToolInvocationLifecycleStatus.FAILED, ToolInvocationLifecycleStatus.CANCELLED}:
            return False
        self.status = ToolInvocationLifecycleStatus.FAILED
        self.reason_code = reason_code[:48]
        self.failed_at = when or timezone.now()
        return True

    def mark_failed(self, *, reason_code: str = "", when=None) -> bool:
        if self.status in {ToolInvocationLifecycleStatus.COMPLETED, ToolInvocationLifecycleStatus.FAILED, ToolInvocationLifecycleStatus.CANCELLED}:
            return False
        self.status = ToolInvocationLifecycleStatus.FAILED
        self.reason_code = reason_code[:48]
        self.failed_at = when or timezone.now()
        return True

    def mark_cancelled(self, *, when=None) -> bool:
        if self.status in {ToolInvocationLifecycleStatus.COMPLETED, ToolInvocationLifecycleStatus.FAILED, ToolInvocationLifecycleStatus.CANCELLED}:
            return False
        self.status = ToolInvocationLifecycleStatus.CANCELLED
        self.failed_at = when or timezone.now()
        return True


# ============================================================================
# WorkspaceSnapshot
# ============================================================================

class WorkspaceSnapshot(models.Model):
    """Versioned, immutable, learner-safe workspace projection.

    Non-authoritative. Never evidence. Never mastery. Never curriculum truth.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        StudyWorkspace,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    snapshot_version = models.PositiveIntegerField(default=1)
    assembled_at = models.DateTimeField(auto_now_add=True)
    workspace_version = models.PositiveIntegerField(default=1)
    context_version = models.PositiveIntegerField(default=1)
    resume_version = models.PositiveIntegerField(default=1)
    source_versions = models.JSONField(default=dict, blank=True)
    panel_projection = models.JSONField(default=list, blank=True)
    tool_projection = models.JSONField(default=list, blank=True)
    session_projection = models.JSONField(default=dict, blank=True)
    journey_projection = models.JSONField(default=dict, blank=True)
    progress_projection = models.JSONField(default=dict, blank=True)
    resource_projection = models.JSONField(default=dict, blank=True)
    next_action_projection = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=24,
        choices=SnapshotStatus.choices,
        default=SnapshotStatus.CURRENT,
    )

    class Meta:
        db_table = "study_lab_snapshot"
        ordering = ["-assembled_at"]
        indexes = [
            models.Index(fields=["workspace", "status"], name="sl_snap_ws_status_idx"),
            models.Index(fields=["workspace", "snapshot_version"], name="sl_snap_ws_version_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "snapshot_version"],
                name="sl_snap_unique_ws_version",
            ),
        ]

    def __str__(self) -> str:
        return f"Snapshot v{self.snapshot_version} for workspace {self.workspace_id}"

    def supersede(self) -> None:
        """Mark this snapshot as superseded by a newer one."""
        if self.status == SnapshotStatus.SUPERSEDED:
            return
        self.status = SnapshotStatus.SUPERSEDED


# ============================================================================
# LearnerWorkspaceNote
# ============================================================================

class LearnerWorkspaceNote(models.Model):
    """Private learner notes attached to a workspace.

    Private by default. Not evidence. Not mastery. Not Ariel memory.
    Not automatically shared with Abbot. Not institution-visible.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        StudyWorkspace,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="study_lab_notes",
    )
    subject_id = models.UUIDField(null=True, blank=True)
    concept_id = models.UUIDField(null=True, blank=True)
    session_reference = models.CharField(max_length=128, blank=True)
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    status = models.CharField(
        max_length=24,
        choices=NoteStatus.choices,
        default=NoteStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "study_lab_note"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["workspace", "status"], name="sl_note_ws_status_idx"),
            models.Index(fields=["learner", "status"], name="sl_note_learner_status_idx"),
            models.Index(fields=["workspace", "subject_id"], name="sl_note_ws_subject_idx"),
        ]

    def __str__(self) -> str:
        return f"Note {self.id} in workspace {self.workspace_id}"

    def clean(self):
        super().clean()
        if self.status == NoteStatus.DELETED and not self.deleted_at:
            raise ValidationError("Deleted notes must record deleted_at.", code="NOTE_DELETED_AT_REQUIRED")

    def archive(self, *, when=None) -> bool:
        if self.status == NoteStatus.ARCHIVED:
            return False
        self.status = NoteStatus.ARCHIVED
        self.version += 1
        return True

    def delete_soft(self, *, when=None) -> bool:
        if self.status == NoteStatus.DELETED:
            return False
        self.status = NoteStatus.DELETED
        self.deleted_at = when or timezone.now()
        self.version += 1
        return True

    def restore(self) -> bool:
        if self.status not in {NoteStatus.ARCHIVED, NoteStatus.DELETED}:
            return False
        self.status = NoteStatus.ACTIVE
        self.deleted_at = None
        self.version += 1
        return True

    @property
    def is_active(self) -> bool:
        return self.status == NoteStatus.ACTIVE

    @property
    def is_deleted(self) -> bool:
        return self.status == NoteStatus.DELETED


# ============================================================================
# WorkspaceActivity
# ============================================================================

class WorkspaceActivity(models.Model):
    """Learner-safe activity record. Never stores private content."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        StudyWorkspace,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="study_lab_activities",
    )
    activity_type = models.CharField(max_length=48, choices=ActivityType.choices)
    provider_context = models.CharField(max_length=32, choices=ProviderContext.choices, null=True, blank=True)
    provider_reference = models.CharField(max_length=128, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "study_lab_activity"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["workspace", "occurred_at"], name="sl_act_ws_time_idx"),
            models.Index(fields=["learner", "occurred_at"], name="sl_act_learner_time_idx"),
            models.Index(fields=["activity_type"], name="sl_act_type_idx"),
        ]

    def __str__(self) -> str:
        return f"Activity {self.activity_type} in workspace {self.workspace_id}"


# ============================================================================
# StudyToolManifest
# ============================================================================

class StudyToolManifest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tool_definition = models.OneToOneField(StudyToolDefinition, on_delete=models.CASCADE, related_name="manifest")
    manifest_version = models.CharField(max_length=32, default="1.0")
    supported_artefact_inputs = models.JSONField(default=list, blank=True)
    supported_artefact_outputs = models.JSONField(default=list, blank=True)
    supported_schema_versions = models.JSONField(default=list, blank=True)
    supports_resume = models.BooleanField(default=False)
    supports_transformation = models.BooleanField(default=False)
    supports_import = models.BooleanField(default=False)
    supports_export = models.BooleanField(default=False)
    status = models.CharField(max_length=24, choices=StudyToolManifestStatus.choices, default=StudyToolManifestStatus.ACTIVE)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "study_lab_tool_manifest"
        ordering = ["tool_definition__tool_key"]


class WorkspaceToolSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(StudyWorkspace, on_delete=models.CASCADE, related_name="tool_sessions")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="study_lab_tool_sessions")
    tool_definition = models.ForeignKey(StudyToolDefinition, on_delete=models.PROTECT, related_name="workspace_sessions")
    provider_context = models.CharField(max_length=32, choices=ProviderContext.choices)
    provider_reference = models.CharField(max_length=128, blank=True)
    resume_reference = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=24, choices=WorkspaceToolSessionStatus.choices, default=WorkspaceToolSessionStatus.OPEN)
    opened_at = models.DateTimeField(auto_now_add=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "study_lab_tool_session"
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["workspace", "status"], name="sl_ts_ws_status_idx"),
            models.Index(fields=["tool_definition", "status"], name="sl_ts_tool_status_idx"),
        ]

    def open(self, *, when=None) -> bool:
        if self.status == WorkspaceToolSessionStatus.OPEN:
            return False
        if self.status not in {WorkspaceToolSessionStatus.SUSPENDED, WorkspaceToolSessionStatus.OPEN}:
            return False
        self.status = WorkspaceToolSessionStatus.OPEN
        self.version += 1
        self.opened_at = self.opened_at or when or timezone.now()
        return True

    def suspend(self, *, when=None) -> bool:
        if self.status != WorkspaceToolSessionStatus.OPEN:
            return False
        self.status = WorkspaceToolSessionStatus.SUSPENDED
        self.suspended_at = when or timezone.now()
        self.version += 1
        return True

    def complete(self, *, when=None) -> bool:
        if self.status not in {WorkspaceToolSessionStatus.OPEN, WorkspaceToolSessionStatus.SUSPENDED}:
            return False
        self.status = WorkspaceToolSessionStatus.COMPLETED
        self.completed_at = when or timezone.now()
        self.version += 1
        return True

    def fail(self, *, when=None) -> bool:
        if self.status not in {WorkspaceToolSessionStatus.OPEN, WorkspaceToolSessionStatus.SUSPENDED}:
            return False
        self.status = WorkspaceToolSessionStatus.FAILED
        self.failed_at = when or timezone.now()
        self.version += 1
        return True

    def abandon(self, *, when=None) -> bool:
        if self.status not in {WorkspaceToolSessionStatus.OPEN, WorkspaceToolSessionStatus.SUSPENDED}:
            return False
        self.status = WorkspaceToolSessionStatus.ABANDONED
        self.failed_at = when or timezone.now()
        self.version += 1
        return True


class WorkspaceToolSessionCommand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(WorkspaceToolSession, on_delete=models.CASCADE, related_name="commands")
    workspace = models.ForeignKey(StudyWorkspace, on_delete=models.CASCADE, related_name="tool_session_commands")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="study_lab_tool_session_commands")
    operation = models.CharField(max_length=24)
    idempotency_key = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=24, default="REQUESTED")
    provider_reference = models.CharField(max_length=128, blank=True)
    failure_code = models.CharField(max_length=64, blank=True)
    reason_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "study_lab_tool_session_command"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["session", "operation", "idempotency_key"], condition=~Q(idempotency_key=""), name="sl_tsc_unique_session_op_idem"),
        ]


class StudyArtefact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(StudyWorkspace, on_delete=models.CASCADE, related_name="artefacts")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="study_lab_artefacts")
    tenant = models.ForeignKey("users.Institution", null=True, blank=True, on_delete=models.PROTECT, related_name="study_lab_artefacts")
    artefact_type = models.CharField(max_length=48, choices=StudyArtefactType.choices)
    provider_context = models.CharField(max_length=32, choices=ProviderContext.choices, null=True, blank=True)
    provider_reference = models.CharField(max_length=128, blank=True)
    title = models.CharField(max_length=255, blank=True)
    summary = models.CharField(max_length=500, blank=True)
    version = models.PositiveIntegerField(default=1)
    visibility = models.CharField(max_length=32, choices=StudyArtefactVisibility.choices, default=StudyArtefactVisibility.PRIVATE)
    lifecycle = models.CharField(max_length=24, choices=StudyArtefactLifecycle.choices, default=StudyArtefactLifecycle.DRAFT)
    schema_version = models.CharField(max_length=32, default="1")
    creation_source = models.CharField(max_length=24, choices=StudyArtefactOrigin.choices, default=StudyArtefactOrigin.NATIVE)
    invocation_reference = models.CharField(max_length=128, blank=True)
    native_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "study_lab_artefact"
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["workspace", "lifecycle"], name="sl_art_ws_life_idx"),
            models.Index(fields=["learner", "visibility"], name="sl_art_learner_vis_idx"),
            models.Index(fields=["artefact_type", "schema_version"], name="sl_art_type_schema_idx"),
        ]

    def archive(self, *, when=None) -> bool:
        if self.lifecycle == StudyArtefactLifecycle.ARCHIVED:
            return False
        self.lifecycle = StudyArtefactLifecycle.ARCHIVED
        self.archived_at = when or timezone.now()
        self.version += 1
        return True

    def supersede(self) -> None:
        self.lifecycle = StudyArtefactLifecycle.SUPERSEDED
        self.version += 1


class StudyArtefactLineage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(StudyWorkspace, on_delete=models.CASCADE, related_name="artefact_lineage")
    source_artefact = models.ForeignKey(StudyArtefact, on_delete=models.CASCADE, related_name="outgoing_lineage")
    target_artefact = models.ForeignKey(StudyArtefact, on_delete=models.CASCADE, related_name="incoming_lineage")
    relation_type = models.CharField(max_length=32, choices=StudyArtefactLineageRelation.choices)
    provider_context = models.CharField(max_length=32, choices=ProviderContext.choices, null=True, blank=True)
    provider_reference = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "study_lab_artefact_lineage"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["workspace", "relation_type"], name="sl_al_ws_rel_idx"),
            models.Index(fields=["source_artefact", "relation_type"], name="sl_al_source_rel_idx"),
            models.Index(fields=["target_artefact", "relation_type"], name="sl_al_target_rel_idx"),
        ]


class StudyArtefactTransformationDefinition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transformation_key = models.CharField(max_length=64, unique=True)
    source_artefact_types = models.JSONField(default=list, blank=True)
    destination_type = models.CharField(max_length=48, choices=StudyArtefactType.choices)
    deterministic = models.BooleanField(default=True)
    provider_context = models.CharField(max_length=32, choices=ProviderContext.choices, null=True, blank=True)
    required_capability = models.CharField(max_length=64, blank=True)
    learner_approval_required = models.BooleanField(default=False)
    supported_schema_versions = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=StudyToolManifestStatus.choices, default=StudyToolManifestStatus.ACTIVE)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "study_lab_artefact_transformation_definition"
        ordering = ["transformation_key"]


class ArtefactTransformationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(StudyWorkspace, on_delete=models.CASCADE, related_name="transformation_requests")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="study_lab_transformation_requests")
    definition = models.ForeignKey(StudyArtefactTransformationDefinition, on_delete=models.PROTECT, related_name="requests")
    source_artefact = models.ForeignKey(StudyArtefact, on_delete=models.PROTECT, related_name="transformation_requests")
    output_artefact = models.ForeignKey(StudyArtefact, null=True, blank=True, on_delete=models.PROTECT, related_name="producing_transformations")
    status = models.CharField(max_length=24, choices=ArtefactTransformationRequestStatus.choices, default=ArtefactTransformationRequestStatus.REQUESTED)
    idempotency_key = models.CharField(max_length=128, blank=True)
    failure_reason = models.CharField(max_length=280, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    validating_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    processing_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "study_lab_artefact_transformation_request"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["workspace", "status"], name="sl_atr_ws_status_idx"),
            models.Index(fields=["definition", "status"], name="sl_atr_def_status_idx"),
            models.Index(fields=["idempotency_key"], name="sl_atr_idem_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["idempotency_key"], condition=~Q(idempotency_key=""), name="sl_atr_unique_idem"),
        ]


class StudyScaffoldGenerationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(StudyWorkspace, on_delete=models.CASCADE, related_name="scaffold_generation_requests")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="study_lab_scaffold_generation_requests")
    generation_type = models.CharField(max_length=48, choices=StudyScaffoldGenerationType.choices)
    requested_artefact_type = models.CharField(max_length=48, choices=StudyArtefactType.choices)
    source_artefacts = models.ManyToManyField(StudyArtefact, related_name="scaffold_generation_sources", blank=True)
    result_artefact = models.ForeignKey(StudyArtefact, null=True, blank=True, on_delete=models.PROTECT, related_name="generated_from_requests")
    provider_context = models.CharField(max_length=32, choices=ProviderContext.choices, default=ProviderContext.STUDY_LAB)
    provider_reference = models.CharField(max_length=128, blank=True)
    policy_version = models.CharField(max_length=32, default="1")
    idempotency_key = models.CharField(max_length=128, blank=True)
    request_checksum = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=24, choices=StudyScaffoldGenerationStatus.choices, default=StudyScaffoldGenerationStatus.REQUESTED)
    failure_code = models.CharField(max_length=64, blank=True)
    failure_detail = models.CharField(max_length=280, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    validating_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    processing_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "study_lab_scaffold_generation_request"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["workspace", "status"], name="sl_sgr_ws_status_idx"),
            models.Index(fields=["learner", "status"], name="sl_sgr_learner_status_idx"),
            models.Index(fields=["idempotency_key"], name="sl_sgr_idem_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["workspace", "generation_type", "idempotency_key"], condition=~Q(idempotency_key=""), name="sl_sgr_unique_ws_type_idem"),
        ]

    def mark_validating(self):
        self.status = StudyScaffoldGenerationStatus.VALIDATING
        self.validating_at = self.validating_at or timezone.now()
        self.version += 1

    def mark_ready(self):
        self.status = StudyScaffoldGenerationStatus.READY
        self.ready_at = self.ready_at or timezone.now()
        self.version += 1

    def mark_processing(self):
        self.status = StudyScaffoldGenerationStatus.PROCESSING
        self.processing_at = self.processing_at or timezone.now()
        self.version += 1

    def mark_completed(self):
        self.status = StudyScaffoldGenerationStatus.COMPLETED
        self.completed_at = timezone.now()
        self.version += 1

    def mark_failed(self, code="", detail=""):
        self.status = StudyScaffoldGenerationStatus.FAILED
        self.failure_code = code[:64]
        self.failure_detail = detail[:280]
        self.failed_at = timezone.now()
        self.version += 1

    def mark_cancelled(self, code=""):
        self.status = StudyScaffoldGenerationStatus.CANCELLED
        self.failure_code = code[:64]
        self.cancelled_at = timezone.now()
        self.version += 1


__all__ = [
    "StudyWorkspace",
    "WorkspaceContext",
    "WorkspaceResumeState",
    "WorkspacePanelDefinition",
    "StudyToolDefinition",
    "WorkspaceToolAvailability",
    "WorkspaceToolInvocation",
    "WorkspaceSnapshot",
    "LearnerWorkspaceNote",
    "WorkspaceActivity",
    "StudyToolManifest",
    "WorkspaceToolSession",
    "WorkspaceToolSessionCommand",
    "StudyArtefact",
    "StudyArtefactLineage",
    "StudyArtefactTransformationDefinition",
    "ArtefactTransformationRequest",
    "StudyScaffoldGenerationRequest",
    "WorkspaceType",
    "WorkspaceStatus",
    "PanelKey",
    "ToolKey",
    "ToolStatus",
    "ToolCategory",
    "ProviderContext",
    "ToolAvailabilityReasonCode",
    "InvocationStatus",
    "NoteStatus",
    "ActivityType",
    "ResumeOutcome",
    "NextActionKey",
    "SnapshotStatus",
    "StudyArtefactType",
    "StudyArtefactVisibility",
    "StudyArtefactLifecycle",
    "StudyArtefactOrigin",
    "StudyArtefactCompatibilityStatus",
    "StudyArtefactLineageRelation",
    "StudyToolManifestStatus",
    "StudyScaffoldGenerationType",
    "StudyScaffoldGenerationStatus",
    "WorkspaceToolSessionStatus",
    "ArtefactTransformationRequestStatus",
    "ToolInvocationLifecycleStatus",
]
