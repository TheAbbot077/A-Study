"""
Study Lab application services.

All lifecycle, privacy, capability, ownership, and tenant policy belongs here.
Study Lab is a composition, orchestration, and workspace projection layer.
It does NOT own curriculum, teaching, retrieval, evidence, or mastery.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db import models
from django.utils import timezone

from apps.study_lab.domain.enums import (
    ActivityType,
    InvocationStatus,
    NextActionKey,
    NoteStatus,
    PanelKey,
    ProviderContext,
    ResumeOutcome,
    SnapshotStatus,
    ToolAvailabilityReasonCode,
    ToolKey,
    ToolStatus,
    WorkspaceStatus,
    WorkspaceType,
)
from apps.study_lab.domain.exceptions import (
    AssemblyProviderFailureError,
    ContextMismatchError,
    ContextNotAccessibleError,
    NoteAccessDeniedError,
    NoteNotFoundError,
    NoteVersionConflictError,
    SnapshotNotAvailableError,
    ToolCapabilityRequiredError,
    ToolNotFoundError,
    ToolProviderUnavailableError,
    ToolUnavailableError,
    WorkspaceInvalidTransitionError,
    WorkspaceAccessDeniedError,
    WorkspaceArchivedError,
    WorkspaceNotActiveError,
    WorkspaceNotFoundError,
    WorkspaceSuspendedError,
    WorkspaceTenantMismatchError,
)
from apps.study_lab.domain.models import (
    LearnerWorkspaceNote,
    StudyToolDefinition,
    StudyWorkspace,
    WorkspaceActivity,
    WorkspaceContext,
    WorkspacePanelDefinition,
    WorkspaceResumeState,
    WorkspaceSnapshot,
    WorkspaceToolAvailability,
    WorkspaceToolInvocation,
)
from apps.study_lab.domain.policies import WorkspaceLifecyclePolicy
from apps.study_lab.application.interoperability_services import LaunchWorkspaceToolService as CanonicalLaunchWorkspaceToolService


# ============================================================================
# Ownership & Authorization Helpers
# ============================================================================

class StudyLabAuthorizationService:
    """Authorization service for Study Lab capabilities.

    Administrative permissions do NOT imply:
    - note access
    - Ariel memory access
    - transcript access
    - private activity access
    """

    @staticmethod
    def is_learner_owner(user_id, workspace_id) -> bool:
        workspace = StudyWorkspace.objects.filter(pk=workspace_id).first()
        return workspace is not None and workspace.learner_id == user_id

    @staticmethod
    def can_view_workspace(user_id, workspace_id) -> bool:
        return StudyLabAuthorizationService.is_learner_owner(user_id, workspace_id)

    @staticmethod
    def can_update_workspace(user_id, workspace_id) -> bool:
        return StudyLabAuthorizationService.is_learner_owner(user_id, workspace_id)

    @staticmethod
    def can_activate_workspace(user_id, workspace_id) -> bool:
        return StudyLabAuthorizationService.is_learner_owner(user_id, workspace_id)

    @staticmethod
    def can_pause_workspace(user_id, workspace_id) -> bool:
        return StudyLabAuthorizationService.is_learner_owner(user_id, workspace_id)

    @staticmethod
    def can_resume_workspace(user_id, workspace_id) -> bool:
        return StudyLabAuthorizationService.is_learner_owner(user_id, workspace_id)

    @staticmethod
    def can_complete_workspace(user_id, workspace_id) -> bool:
        return StudyLabAuthorizationService.is_learner_owner(user_id, workspace_id)

    @staticmethod
    def can_archive_workspace(user_id, workspace_id) -> bool:
        return StudyLabAuthorizationService.is_learner_owner(user_id, workspace_id)

    @staticmethod
    def can_create_workspace(user_id) -> bool:
        """Learners can always create workspaces."""
        return True

    @staticmethod
    def can_use_tools(user_id, workspace_id) -> bool:
        return StudyLabAuthorizationService.is_learner_owner(user_id, workspace_id)

    @staticmethod
    def can_create_note(user_id, workspace_id) -> bool:
        return StudyLabAuthorizationService.is_learner_owner(user_id, workspace_id)

    @staticmethod
    def can_view_note(user_id, workspace_id, note_id) -> bool:
        note = LearnerWorkspaceNote.objects.filter(pk=note_id, workspace_id=workspace_id).first()
        return note is not None and note.learner_id == user_id

    @staticmethod
    def can_update_note(user_id, workspace_id, note_id) -> bool:
        return StudyLabAuthorizationService.can_view_note(user_id, workspace_id, note_id)

    @staticmethod
    def can_delete_note(user_id, workspace_id, note_id) -> bool:
        return StudyLabAuthorizationService.can_view_note(user_id, workspace_id, note_id)

    @staticmethod
    def can_admin_view_status(user_id) -> bool:
        """Admin can view operational status only — not private content."""
        return False  # No admin bypass for private content

    @staticmethod
    def can_institution_access_notes(user_id, workspace_id) -> bool:
        """Institutions can never access learner notes."""
        return False

    @staticmethod
    def can_institution_access_activity(user_id, workspace_id) -> bool:
        """Institutions can never access detailed activity streams."""
        return False

    @staticmethod
    def can_institution_access_transcripts(user_id, workspace_id) -> bool:
        """Institutions can never access Ariel or Abbot transcripts."""
        return False


# ============================================================================
# Workspace Lifecycle Services
# ============================================================================

class CreateStudyWorkspaceService:
    """Create a new Study Workspace for a learner."""

    @staticmethod
    @transaction.atomic
    def execute(
        learner_id,
        workspace_type=WorkspaceType.SELF_STUDY,
        title="",
        tenant_id=None,
        created_by_id=None,
        idempotency_key=None,
    ):
        if not StudyLabAuthorizationService.can_create_workspace(learner_id):
            raise WorkspaceAccessDeniedError()

        created_by_id = created_by_id or learner_id

        # Idempotency check
        if idempotency_key:
            existing = StudyWorkspace.objects.filter(metadata__idempotency_key=idempotency_key).first()
            if existing:
                return existing

        # Tenant validation
        if workspace_type in {WorkspaceType.SELF_STUDY, WorkspaceType.PERSONAL_REVIEW}:
            if tenant_id is not None:
                raise WorkspaceTenantMismatchError()
        elif workspace_type in {WorkspaceType.INSTITUTIONAL, WorkspaceType.HYBRID}:
            if tenant_id is None:
                raise WorkspaceTenantMismatchError()

        workspace = StudyWorkspace.objects.create(
            learner_id=learner_id,
            tenant_id=tenant_id,
            workspace_type=workspace_type,
            title=title,
            created_by_id=created_by_id,
            status=WorkspaceStatus.DRAFT,
        )

        # Create context
        WorkspaceContext.objects.create(workspace=workspace)

        # Create resume state
        WorkspaceResumeState.objects.create(
            workspace=workspace,
            last_panel_key=PanelKey.MENTOR,
            last_activity_type=ActivityType.WORKSPACE_CREATED,
        )

        # Record activity
        WorkspaceActivity.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            activity_type=ActivityType.WORKSPACE_CREATED,
            provider_context=ProviderContext.STUDY_LAB,
        )

        # Publish event
        from apps.study_lab.domain.events import StudyWorkspaceCreated
        event = StudyWorkspaceCreated(
            workspace_id=workspace.id,
            learner_id=learner_id,
            tenant_id=tenant_id,
            workspace_type=workspace_type,
        )
        _publish_event(event)

        return workspace


class ActivateStudyWorkspaceService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if not workspace.is_mutable:
            raise WorkspaceArchivedError()
        if workspace.status == WorkspaceStatus.ACTIVE:
            return workspace
        if not WorkspaceLifecyclePolicy.can_transition(workspace.status, WorkspaceStatus.ACTIVE):
            raise WorkspaceInvalidTransitionError(workspace.status, WorkspaceStatus.ACTIVE)

        workspace.activate()
        workspace.save()

        WorkspaceActivity.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            activity_type=ActivityType.WORKSPACE_ACTIVATED,
            provider_context=ProviderContext.STUDY_LAB,
        )

        from apps.study_lab.domain.events import StudyWorkspaceActivated
        _publish_event(StudyWorkspaceActivated(workspace_id, learner_id))

        return workspace


class PauseStudyWorkspaceService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if not workspace.is_mutable:
            raise WorkspaceArchivedError()
        if not WorkspaceLifecyclePolicy.can_transition(workspace.status, WorkspaceStatus.PAUSED):
            raise WorkspaceInvalidTransitionError(workspace.status, WorkspaceStatus.PAUSED)

        workspace.pause()
        workspace.save()

        WorkspaceActivity.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            activity_type=ActivityType.WORKSPACE_PAUSED,
            provider_context=ProviderContext.STUDY_LAB,
        )

        from apps.study_lab.domain.events import StudyWorkspacePaused
        _publish_event(StudyWorkspacePaused(workspace_id, learner_id))

        return workspace


class ResumeStudyWorkspaceService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if not workspace.is_mutable:
            raise WorkspaceArchivedError()
        if not WorkspaceLifecyclePolicy.can_transition(workspace.status, WorkspaceStatus.ACTIVE):
            raise WorkspaceInvalidTransitionError(workspace.status, WorkspaceStatus.ACTIVE)

        workspace.resume()
        workspace.save()

        WorkspaceActivity.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            activity_type=ActivityType.WORKSPACE_RESUMED,
            provider_context=ProviderContext.STUDY_LAB,
        )

        from apps.study_lab.domain.events import StudyWorkspaceResumed
        _publish_event(StudyWorkspaceResumed(workspace_id, learner_id))

        return workspace


class SuspendStudyWorkspaceService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if not workspace.is_mutable:
            raise WorkspaceArchivedError()
        if not WorkspaceLifecyclePolicy.can_transition(workspace.status, WorkspaceStatus.SUSPENDED):
            raise WorkspaceInvalidTransitionError(workspace.status, WorkspaceStatus.SUSPENDED)

        workspace.suspend()
        workspace.save()

        WorkspaceActivity.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            activity_type=ActivityType.WORKSPACE_OPENED,
            provider_context=ProviderContext.STUDY_LAB,
        )

        from apps.study_lab.domain.events import StudyWorkspaceSuspended
        _publish_event(StudyWorkspaceSuspended(workspace_id, learner_id))

        return workspace


class CompleteStudyWorkspaceService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if not workspace.is_mutable:
            raise WorkspaceArchivedError()
        if not WorkspaceLifecyclePolicy.can_transition(workspace.status, WorkspaceStatus.COMPLETED):
            raise WorkspaceInvalidTransitionError(workspace.status, WorkspaceStatus.COMPLETED)

        workspace.complete()
        workspace.save()

        WorkspaceActivity.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            activity_type=ActivityType.WORKSPACE_COMPLETED,
            provider_context=ProviderContext.STUDY_LAB,
        )

        from apps.study_lab.domain.events import StudyWorkspaceCompleted
        _publish_event(StudyWorkspaceCompleted(workspace_id, learner_id))

        return workspace


class ArchiveStudyWorkspaceService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if not workspace.is_mutable:
            raise WorkspaceArchivedError()
        if not WorkspaceLifecyclePolicy.can_transition(workspace.status, WorkspaceStatus.ARCHIVED):
            raise WorkspaceInvalidTransitionError(workspace.status, WorkspaceStatus.ARCHIVED)

        workspace.archive()
        workspace.save()

        WorkspaceActivity.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            activity_type=ActivityType.WORKSPACE_ARCHIVED,
            provider_context=ProviderContext.STUDY_LAB,
        )

        from apps.study_lab.domain.events import StudyWorkspaceArchived
        _publish_event(StudyWorkspaceArchived(workspace_id, learner_id))

        return workspace


class RestoreStudyWorkspaceService:
    """Restore an archived workspace (admin-only)."""

    @staticmethod
    @transaction.atomic
    def execute(workspace_id, admin_user_id):
        workspace = StudyWorkspace.objects.filter(pk=workspace_id).first()
        if not workspace:
            raise WorkspaceNotFoundError(workspace_id)
        if workspace.status != WorkspaceStatus.ARCHIVED:
            raise ValidationError("Only archived workspaces can be restored.", code="WORKSPACE_NOT_ARCHIVED")

        workspace.status = WorkspaceStatus.ACTIVE
        workspace.archived_at = None
        workspace.activated_at = timezone.now()
        workspace.version += 1
        workspace.save()

        from apps.study_lab.domain.events import StudyWorkspaceRestored
        _publish_event(StudyWorkspaceRestored(workspace_id, workspace.learner_id))

        return workspace


# ============================================================================
# Workspace Context Services
# ============================================================================

class SetWorkspaceContextService:
    """Set or update the active study context for a workspace."""

    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, **context_fields):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if not workspace.is_mutable:
            raise WorkspaceArchivedError()

        context_id = context_fields.pop("context_id", None)
        if context_id:
            context = WorkspaceContext.objects.filter(pk=context_id).select_related("workspace").first()
            if not context:
                raise ContextNotAccessibleError("context")
            if context.workspace_id != workspace.id:
                raise ContextMismatchError()
            if context.workspace.learner_id != learner_id:
                raise ContextNotAccessibleError("context")
        else:
            context = workspace.context
            if not context:
                context = WorkspaceContext.objects.create(workspace=workspace)

        # Validate tenant compatibility
        for field_name, value in context_fields.items():
            if field_name in {
                "active_learning_journey_id",
                "active_institutional_journey_id",
                "active_subject_id",
                "active_course_id",
                "active_programme_id",
                "active_curriculum_reference_id",
                "active_competency_id",
                "active_concept_id",
                "active_abbot_session_id",
                "active_ariel_session_id",
                "active_whiteboard_session_id",
                "active_concept_check_id",
            }:
                setattr(context, field_name, value)

        context.update_version()
        context.save()

        WorkspaceActivity.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            activity_type=ActivityType.CONTEXT_CHANGED,
            provider_context=ProviderContext.STUDY_LAB,
        )

        from apps.study_lab.domain.events import WorkspaceContextChanged
        _publish_event(WorkspaceContextChanged(workspace_id, learner_id, context.version))

        return context


class ClearWorkspaceContextService:
    """Clear specific context references from a workspace."""

    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, fields_to_clear):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if not workspace.is_mutable:
            raise WorkspaceArchivedError()

        context = workspace.context
        if not context:
            return None

        for field_name in fields_to_clear:
            if hasattr(context, field_name):
                setattr(context, field_name, None)

        context.update_version()
        context.save()

        from apps.study_lab.domain.events import WorkspaceContextChanged
        _publish_event(WorkspaceContextChanged(workspace_id, learner_id, context.version))

        return context


# ============================================================================
# Resume State Services
# ============================================================================

class UpdateWorkspaceResumeStateService:
    """Update the learner-safe resume point for a workspace."""

    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, **resume_fields):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if not workspace.is_mutable:
            raise WorkspaceArchivedError()

        resume_state = workspace.resume_state
        if not resume_state:
            resume_state = WorkspaceResumeState.objects.create(
                workspace=workspace,
                last_panel_key=PanelKey.MENTOR,
                last_activity_type=ActivityType.WORKSPACE_CREATED,
            )

        for field_name, value in resume_fields.items():
            if hasattr(resume_state, field_name):
                setattr(resume_state, field_name, value)

        resume_state.update_version()
        resume_state.save()

        from apps.study_lab.domain.events import WorkspaceResumePointUpdated
        _publish_event(WorkspaceResumePointUpdated(workspace_id, learner_id, resume_state.version))

        return resume_state


class ResolveWorkspaceResumePointService:
    """Deterministically decide where the learner resumes."""

    @staticmethod
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        resume_state = workspace.resume_state
        if not resume_state:
            return {
                "outcome": ResumeOutcome.NO_ACTIVE_RESUME_POINT,
                "workspace_id": str(workspace_id),
                "learner_id": str(learner_id),
            }

        context = workspace.context

        # Priority: active sessions first
        if context and context.active_abbot_session_id:
            return {
                "outcome": ResumeOutcome.RESUME_ABBOT_SESSION,
                "workspace_id": str(workspace_id),
                "learner_id": str(learner_id),
                "session_id": str(context.active_abbot_session_id),
                "panel_key": resume_state.last_panel_key,
            }

        if context and context.active_ariel_session_id:
            return {
                "outcome": ResumeOutcome.RESUME_ARIEL_SESSION,
                "workspace_id": str(workspace_id),
                "learner_id": str(learner_id),
                "session_id": str(context.active_ariel_session_id),
                "panel_key": resume_state.last_panel_key,
            }

        if context and context.active_whiteboard_session_id:
            return {
                "outcome": ResumeOutcome.RESUME_WHITEBOARD,
                "workspace_id": str(workspace_id),
                "learner_id": str(learner_id),
                "session_id": str(context.active_whiteboard_session_id),
                "panel_key": resume_state.last_panel_key,
            }

        if context and context.active_concept_check_id:
            return {
                "outcome": ResumeOutcome.RESUME_CONCEPT_CHECK,
                "workspace_id": str(workspace_id),
                "learner_id": str(learner_id),
                "session_id": str(context.active_concept_check_id),
                "panel_key": resume_state.last_panel_key,
            }

        if context and context.active_subject_id:
            return {
                "outcome": ResumeOutcome.RETURN_TO_SUBJECT,
                "workspace_id": str(workspace_id),
                "learner_id": str(learner_id),
                "subject_id": str(context.active_subject_id),
                "panel_key": resume_state.last_panel_key,
            }

        if context and context.active_learning_journey_id:
            return {
                "outcome": ResumeOutcome.RETURN_TO_JOURNEY,
                "workspace_id": str(workspace_id),
                "learner_id": str(learner_id),
                "journey_id": str(context.active_learning_journey_id),
                "panel_key": resume_state.last_panel_key,
            }

        return {
            "outcome": ResumeOutcome.NO_ACTIVE_RESUME_POINT,
            "workspace_id": str(workspace_id),
            "learner_id": str(learner_id),
        }


# ============================================================================
# Panel Resolution Service
# ============================================================================

class ResolveWorkspacePanelsService:
    """Resolve available panels for a workspace."""

    @staticmethod
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)

        panels = WorkspacePanelDefinition.objects.filter(status=ToolStatus.ACTIVE)
        result = []
        for panel in panels:
            if not panel.supports_workspace_type(workspace.workspace_type):
                continue
            result.append({
                "panel_key": panel.panel_key,
                "display_name": panel.display_name,
                "description": panel.description,
                "provider_context": panel.provider_context,
                "required_capability": panel.required_capability,
                "sort_order": panel.sort_order,
                "version": panel.version,
            })
        return sorted(result, key=lambda x: x["sort_order"])


# ============================================================================
# Tool Availability Service
# ============================================================================

class ResolveWorkspaceToolAvailabilityService:
    """Evaluate and persist tool availability for a workspace."""

    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)

        tools = StudyToolDefinition.objects.filter(status=ToolStatus.ACTIVE)
        results = []

        for tool in tools:
            if not tool.supports_workspace_type(workspace.workspace_type):
                availability = _upsert_availability(
                    workspace, tool, False,
                    ToolAvailabilityReasonCode.WORKSPACE_NOT_ACTIVE,
                    f"Tool does not support workspace type {workspace.workspace_type}",
                )
                results.append(_availability_to_dict(availability))
                continue

            # Check workspace lifecycle
            if workspace.is_archived:
                availability = _upsert_availability(
                    workspace, tool, False,
                    ToolAvailabilityReasonCode.WORKSPACE_ARCHIVED,
                    "Workspace is archived",
                )
                results.append(_availability_to_dict(availability))
                continue

            if workspace.is_suspended:
                availability = _upsert_availability(
                    workspace, tool, False,
                    ToolAvailabilityReasonCode.WORKSPACE_SUSPENDED,
                    "Workspace is suspended",
                )
                results.append(_availability_to_dict(availability))
                continue

            if not workspace.is_active:
                availability = _upsert_availability(
                    workspace, tool, False,
                    ToolAvailabilityReasonCode.WORKSPACE_NOT_ACTIVE,
                    "Workspace is not active",
                )
                results.append(_availability_to_dict(availability))
                continue

            # Check capability requirement
            if tool.required_capability:
                if not StudyLabAuthorizationService.is_learner_owner(learner_id, workspace_id):
                    availability = _upsert_availability(
                        workspace, tool, False,
                        ToolAvailabilityReasonCode.CAPABILITY_REQUIRED,
                        f"Capability required: {tool.required_capability}",
                    )
                    results.append(_availability_to_dict(availability))
                    continue

            # Provider-specific checks
            reason_code, reason_detail = _evaluate_provider_availability(tool, workspace)
            available = reason_code == ToolAvailabilityReasonCode.AVAILABLE

            availability = _upsert_availability(
                workspace, tool, available, reason_code, reason_detail,
            )
            results.append(_availability_to_dict(availability))

        return results


def _upsert_availability(workspace, tool, available, reason_code, reason_detail):
    availability, _created = WorkspaceToolAvailability.objects.update_or_create(
        workspace=workspace,
        tool_definition=tool,
        defaults={
            "available": available,
            "reason_code": reason_code,
            "reason_detail": reason_detail[:280],
            "source_versions": {},
            "version": 1,
        },
    )
    return availability


def _availability_to_dict(availability):
    return {
        "tool_key": availability.tool_definition.tool_key,
        "display_name": availability.tool_definition.display_name,
        "available": availability.available,
        "reason_code": availability.reason_code,
        "reason_detail": availability.reason_detail,
        "evaluated_at": availability.evaluated_at.isoformat() if availability.evaluated_at else None,
        "version": availability.version,
    }


def _evaluate_provider_availability(tool, workspace):
    """Evaluate provider-specific availability. Uses adapter contracts."""
    from apps.study_lab.infrastructure.adapters import ProviderAdapterRegistry

    adapter = ProviderAdapterRegistry.get_adapter(tool.provider_context)
    if adapter is None:
        return (
            ToolAvailabilityReasonCode.PROVIDER_UNAVAILABLE,
            f"No adapter for provider {tool.provider_context}",
        )

    try:
        return adapter.evaluate_availability(workspace, tool)
    except Exception:
        return (
            ToolAvailabilityReasonCode.PROVIDER_UNAVAILABLE,
            f"Provider {tool.provider_context} evaluation failed",
        )


# ============================================================================
# Tool Invocation Service
# ============================================================================

class InvokeWorkspaceToolService:
    """Invoke a tool through its provider adapter."""

    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, tool_key, idempotency_key=None, **kwargs):
        session, invocation = CanonicalLaunchWorkspaceToolService.execute(
            workspace_id,
            learner_id,
            tool_key,
            input_artefact_ids=kwargs.get("input_artefact_ids"),
            idempotency_key=idempotency_key or "",
        )
        return invocation


# ============================================================================
# Workspace Assembly Service
# ============================================================================

class AssembleStudyWorkspaceService:
    """Central deterministic composition service.

    Assembles a learner-safe projection of the workspace.
    Never becomes a persistence dumping ground.
    """

    @staticmethod
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)

        # Resolve panels
        panels = ResolveWorkspacePanelsService.execute(workspace_id, learner_id)

        # Resolve tool availability
        tools = ResolveWorkspaceToolAvailabilityService.execute(workspace_id, learner_id)

        # Resolve resume point
        resume = ResolveWorkspaceResumeStateService.execute(workspace_id, learner_id)

        # Provider projections
        session_projection = _project_session(workspace)
        journey_projection = _project_journey(workspace)
        progress_projection = _project_progress(workspace)
        resource_projection = _project_resources(workspace)
        next_action = _project_next_action(workspace, resume)

        # Source versions
        source_versions = {}
        if workspace.context:
            source_versions.update(workspace.context.source_versions or {})
        source_versions["workspace_version"] = workspace.version
        if workspace.resume_state:
            source_versions["resume_version"] = workspace.resume_state.version
        if workspace.context:
            source_versions["context_version"] = workspace.context.version

        return {
            "workspace_id": str(workspace.id),
            "learner_id": str(workspace.learner_id),
            "workspace_type": workspace.workspace_type,
            "status": workspace.status,
            "title": workspace.title,
            "tenant_id": str(workspace.tenant_id) if workspace.tenant_id else None,
            "ownership": {
                "learner_id": str(workspace.learner_id),
                "created_by_id": str(workspace.created_by_id),
            },
            "active_context": _project_context(workspace),
            "resume_state": resume,
            "panels": panels,
            "tools": tools,
            "session_projection": session_projection,
            "journey_projection": journey_projection,
            "progress_projection": progress_projection,
            "resource_projection": resource_projection,
            "next_action": next_action,
            "privacy_flags": {
                "notes_private": True,
                "ariel_memory_private": True,
                "abbro_t_transcripts_private": True,
                "activity_private": True,
            },
            "source_versions": source_versions,
            "generated_at": timezone.now().isoformat(),
        }


def _project_context(workspace):
    if not workspace.context:
        return None
    ctx = workspace.context
    return {
        "active_learning_journey_id": str(ctx.active_learning_journey_id) if ctx.active_learning_journey_id else None,
        "active_institutional_journey_id": str(ctx.active_institutional_journey_id) if ctx.active_institutional_journey_id else None,
        "active_subject_id": str(ctx.active_subject_id) if ctx.active_subject_id else None,
        "active_course_id": str(ctx.active_course_id) if ctx.active_course_id else None,
        "active_programme_id": str(ctx.active_programme_id) if ctx.active_programme_id else None,
        "active_competency_id": str(ctx.active_competency_id) if ctx.active_competency_id else None,
        "active_concept_id": str(ctx.active_concept_id) if ctx.active_concept_id else None,
        "active_abbot_session_id": str(ctx.active_abbot_session_id) if ctx.active_abbot_session_id else None,
        "active_ariel_session_id": str(ctx.active_ariel_session_id) if ctx.active_ariel_session_id else None,
        "active_whiteboard_session_id": str(ctx.active_whiteboard_session_id) if ctx.active_whiteboard_session_id else None,
        "active_concept_check_id": str(ctx.active_concept_check_id) if ctx.active_concept_check_id else None,
        "version": ctx.version,
    }


def _project_session(workspace):
    """Project session status from provider adapters."""
    from apps.study_lab.infrastructure.adapters import ProviderAdapterRegistry

    projection = {}
    ctx = workspace.context
    if not ctx:
        return projection

    for provider, session_id_attr in [
        (ProviderContext.ABBOT, "active_abbot_session_id"),
        (ProviderContext.ARIEL, "active_ariel_session_id"),
        (ProviderContext.WHITEBOARD, "active_whiteboard_session_id"),
        (ProviderContext.CONCEPT_CHECK, "active_concept_check_id"),
    ]:
        session_id = getattr(ctx, session_id_attr, None)
        if session_id:
            adapter = ProviderAdapterRegistry.get_adapter(provider)
            if adapter:
                try:
                    projection[provider.lower()] = adapter.project_session(session_id)
                except Exception:
                    projection[provider.lower()] = {"status": "provider_unavailable"}
            else:
                projection[provider.lower()] = {"status": "no_adapter"}

    return projection


def _project_journey(workspace):
    """Project journey status from provider adapters."""
    from apps.study_lab.infrastructure.adapters import ProviderAdapterRegistry

    ctx = workspace.context
    if not ctx or not ctx.active_learning_journey_id:
        return {}

    adapter = ProviderAdapterRegistry.get_adapter(ProviderContext.JOURNEY)
    if adapter:
        try:
            return adapter.project_journey(ctx.active_learning_journey_id)
        except Exception:
            return {"status": "provider_unavailable"}
    return {"status": "no_adapter"}


def _project_progress(workspace):
    """Project learner-safe progress from provider adapters."""
    from apps.study_lab.infrastructure.adapters import ProviderAdapterRegistry

    adapter = ProviderAdapterRegistry.get_adapter(ProviderContext.PROGRESS)
    if adapter:
        try:
            return adapter.project_progress(workspace.learner_id, workspace.id)
        except Exception:
            return {"status": "provider_unavailable"}
    return {"status": "no_adapter"}


def _project_resources(workspace):
    """Project resource availability from provider adapters."""
    from apps.study_lab.infrastructure.adapters import ProviderAdapterRegistry

    adapter = ProviderAdapterRegistry.get_adapter(ProviderContext.RESOURCE)
    if adapter:
        try:
            return adapter.project_resources(workspace)
        except Exception:
            return {"status": "provider_unavailable"}
    return {"status": "no_adapter"}


def _project_next_action(workspace, resume):
    """Determine the recommended next action."""
    outcome = resume.get("outcome")

    if outcome == ResumeOutcome.RESUME_ABBOT_SESSION:
        return {"action_key": NextActionKey.CONTINUE_TEACHING, "provider": "ABBOT"}
    if outcome == ResumeOutcome.RESUME_ARIEL_SESSION:
        return {"action_key": NextActionKey.TEACH_ARIEL, "provider": "ARIEL"}
    if outcome == ResumeOutcome.RESUME_WHITEBOARD:
        return {"action_key": NextActionKey.RESUME_WHITEBOARD, "provider": "WHITEBOARD"}
    if outcome == ResumeOutcome.RESUME_CONCEPT_CHECK:
        return {"action_key": NextActionKey.COMPLETE_CONCEPT_CHECK, "provider": "CONCEPT_CHECK"}
    if outcome == ResumeOutcome.RETURN_TO_SUBJECT:
        return {"action_key": NextActionKey.REVIEW_CONCEPT, "provider": "STUDY_LAB"}
    if outcome == ResumeOutcome.RETURN_TO_JOURNEY:
        return {"action_key": NextActionKey.RETURN_TO_JOURNEY, "provider": "JOURNEY"}
    if outcome == ResumeOutcome.OPEN_RECOMMENDED_RESOURCE:
        return {"action_key": NextActionKey.OPEN_RESOURCE, "provider": "RESOURCE"}
    if outcome == ResumeOutcome.START_NEXT_CONCEPT:
        return {"action_key": NextActionKey.START_NEXT_CONCEPT, "provider": "JOURNEY"}

    return {"action_key": NextActionKey.NO_RECOMMENDATION, "provider": "STUDY_LAB"}


# ============================================================================
# Snapshot Services
# ============================================================================

class CreateWorkspaceSnapshotService:
    """Create an immutable, versioned snapshot of the workspace assembly."""

    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id):
        workspace = _get_owned_workspace(workspace_id, learner_id)

        # Mark previous current snapshot as stale
        WorkspaceSnapshot.objects.filter(
            workspace=workspace,
            status=SnapshotStatus.CURRENT,
        ).update(status=SnapshotStatus.STALE)

        # Assemble
        assembly = AssembleStudyWorkspaceService.execute(workspace_id, learner_id)

        # Determine next version
        latest = WorkspaceSnapshot.objects.filter(workspace=workspace).order_by("-snapshot_version").first()
        next_version = (latest.snapshot_version + 1) if latest else 1

        snapshot = WorkspaceSnapshot.objects.create(
            workspace=workspace,
            snapshot_version=next_version,
            workspace_version=workspace.version,
            context_version=workspace.context.version if workspace.context else 0,
            resume_version=workspace.resume_state.version if workspace.resume_state else 0,
            source_versions=assembly["source_versions"],
            panel_projection=assembly["panels"],
            tool_projection=assembly["tools"],
            session_projection=assembly["session_projection"],
            journey_projection=assembly["journey_projection"],
            progress_projection=assembly["progress_projection"],
            resource_projection=assembly["resource_projection"],
            next_action_projection=assembly["next_action"],
            status=SnapshotStatus.CURRENT,
        )

        from apps.study_lab.domain.events import WorkspaceSnapshotCreated
        _publish_event(WorkspaceSnapshotCreated(workspace_id, learner_id, next_version))

        return snapshot


class MarkWorkspaceSnapshotStaleService:
    """Mark a snapshot as stale (e.g., after context change)."""

    @staticmethod
    def execute(workspace_id, learner_id, snapshot_version=None):
        workspace = _get_owned_workspace(workspace_id, learner_id)

        if snapshot_version:
            snapshots = WorkspaceSnapshot.objects.filter(
                workspace=workspace,
                snapshot_version=snapshot_version,
            )
        else:
            snapshots = WorkspaceSnapshot.objects.filter(
                workspace=workspace,
                status=SnapshotStatus.CURRENT,
            )

        snapshots.update(status=SnapshotStatus.STALE)

        for snap in snapshots:
            from apps.study_lab.domain.events import WorkspaceSnapshotMarkedStale
            _publish_event(WorkspaceSnapshotMarkedStale(workspace_id, learner_id, snap.snapshot_version))

        return snapshots.count()


# ============================================================================
# Learner Notes Services
# ============================================================================

class CreateLearnerWorkspaceNoteService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, title="", content="", subject_id=None, concept_id=None, session_reference=""):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if not workspace.is_mutable:
            raise WorkspaceArchivedError()

        note = LearnerWorkspaceNote.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            title=title,
            content=content,
            subject_id=subject_id,
            concept_id=concept_id,
            session_reference=session_reference,
            status=NoteStatus.ACTIVE,
        )

        WorkspaceActivity.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            activity_type=ActivityType.NOTE_CREATED,
            provider_context=ProviderContext.STUDY_LAB,
        )

        from apps.study_lab.domain.events import LearnerWorkspaceNoteCreated
        _publish_event(LearnerWorkspaceNoteCreated(workspace_id, learner_id, note.id))

        return note


class UpdateLearnerWorkspaceNoteService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, note_id, title=None, content=None, version=None):
        note = LearnerWorkspaceNote.objects.filter(
            pk=note_id,
            workspace_id=workspace_id,
            learner_id=learner_id,
        ).first()
        if not note:
            raise NoteNotFoundError(note_id)
        if not note.is_active:
            raise NoteAccessDeniedError()

        # Optimistic versioning
        if version is not None and note.version != version:
            raise NoteVersionConflictError()

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        note.version += 1
        note.save()

        WorkspaceActivity.objects.create(
            workspace_id=workspace_id,
            learner_id=learner_id,
            activity_type=ActivityType.NOTE_UPDATED,
            provider_context=ProviderContext.STUDY_LAB,
        )

        from apps.study_lab.domain.events import LearnerWorkspaceNoteUpdated
        _publish_event(LearnerWorkspaceNoteUpdated(workspace_id, learner_id, note.id))

        return note


class ArchiveLearnerWorkspaceNoteService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, note_id):
        note = LearnerWorkspaceNote.objects.filter(
            pk=note_id,
            workspace_id=workspace_id,
            learner_id=learner_id,
        ).first()
        if not note:
            raise NoteNotFoundError(note_id)
        if not note.is_active:
            raise NoteAccessDeniedError()

        note.archive()
        note.save()

        from apps.study_lab.domain.events import LearnerWorkspaceNoteArchived
        _publish_event(LearnerWorkspaceNoteArchived(workspace_id, learner_id, note.id))

        return note


class DeleteLearnerWorkspaceNoteService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, note_id):
        note = LearnerWorkspaceNote.objects.filter(
            pk=note_id,
            workspace_id=workspace_id,
            learner_id=learner_id,
        ).first()
        if not note:
            raise NoteNotFoundError(note_id)
        if not note.is_active:
            raise NoteAccessDeniedError()

        note.delete_soft()
        note.save()

        from apps.study_lab.domain.events import LearnerWorkspaceNoteDeleted
        _publish_event(LearnerWorkspaceNoteDeleted(workspace_id, learner_id, note.id))

        return note


# ============================================================================
# Activity Recording Service
# ============================================================================

class RecordWorkspaceActivityService:
    """Record learner-safe activity. Never stores private content."""

    @staticmethod
    def execute(workspace_id, learner_id, activity_type, provider_context=None, provider_reference="", metadata=None):
        workspace = _get_owned_workspace(workspace_id, learner_id)

        activity = WorkspaceActivity.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            activity_type=activity_type,
            provider_context=provider_context or ProviderContext.STUDY_LAB,
            provider_reference=provider_reference[:128],
            metadata=metadata or {},
        )

        return activity


# ============================================================================
# Tool Registry Seeding
# ============================================================================

class SeedStudyToolRegistryService:
    """Seed the tool and panel registry with default definitions."""

    @staticmethod
    @transaction.atomic
    def execute():
        panels = [
            {
                "panel_key": PanelKey.MENTOR,
                "display_name": "Mentor",
                "description": "Abbot teaching session",
                "provider_context": ProviderContext.ABBOT,
                "required_capability": "",
                "supported_workspace_types": [],
                "sort_order": 10,
            },
            {
                "panel_key": PanelKey.WHITEBOARD,
                "display_name": "Whiteboard",
                "description": "Structured whiteboard",
                "provider_context": ProviderContext.WHITEBOARD,
                "required_capability": "",
                "supported_workspace_types": [],
                "sort_order": 20,
            },
            {
                "panel_key": PanelKey.RESOURCES,
                "display_name": "Resources",
                "description": "Governed learning resources",
                "provider_context": ProviderContext.RESOURCE,
                "required_capability": "",
                "supported_workspace_types": [],
                "sort_order": 30,
            },
            {
                "panel_key": PanelKey.ARIEL,
                "display_name": "Ariel",
                "description": "Learner-taught memory companion",
                "provider_context": ProviderContext.ARIEL,
                "required_capability": "ariel.use",
                "supported_workspace_types": [],
                "sort_order": 40,
            },
            {
                "panel_key": PanelKey.CONCEPT_CHECK,
                "display_name": "Concept Check",
                "description": "Concept checks and assessments",
                "provider_context": ProviderContext.CONCEPT_CHECK,
                "required_capability": "",
                "supported_workspace_types": [],
                "sort_order": 50,
            },
            {
                "panel_key": PanelKey.PROGRESS,
                "display_name": "Progress",
                "description": "Learner-safe progress view",
                "provider_context": ProviderContext.PROGRESS,
                "required_capability": "",
                "supported_workspace_types": [],
                "sort_order": 60,
            },
            {
                "panel_key": PanelKey.NOTES,
                "display_name": "Notes",
                "description": "Private learner notes",
                "provider_context": ProviderContext.STUDY_LAB,
                "required_capability": "",
                "supported_workspace_types": [],
                "sort_order": 70,
            },
            {
                "panel_key": PanelKey.JOURNEY,
                "display_name": "Journey",
                "description": "Learning journey map",
                "provider_context": ProviderContext.JOURNEY,
                "required_capability": "",
                "supported_workspace_types": [],
                "sort_order": 80,
            },
            {
                "panel_key": PanelKey.ACTIVITY,
                "display_name": "Activity",
                "description": "Learner-safe activity history",
                "provider_context": ProviderContext.STUDY_LAB,
                "required_capability": "",
                "supported_workspace_types": [],
                "sort_order": 90,
            },
        ]

        for panel_data in panels:
            WorkspacePanelDefinition.objects.update_or_create(
                panel_key=panel_data["panel_key"],
                defaults=panel_data,
            )

        tools = [
            {
                "tool_key": ToolKey.ABBOT_MENTOR,
                "display_name": "Abbot Mentor",
                "description": "Open or resume an Abbot teaching session",
                "category": "TEACHING",
                "provider_context": ProviderContext.ABBOT,
                "required_capability": "",
                "supported_workspace_types": [],
                "policy_key": "abbott_teach",
                "status": ToolStatus.ACTIVE,
            },
            {
                "tool_key": ToolKey.ARIEL_TEACH,
                "display_name": "Ariel Teach",
                "description": "Teach or review Ariel memory",
                "category": "LEARNING",
                "provider_context": ProviderContext.ARIEL,
                "required_capability": "ariel.use",
                "supported_workspace_types": [],
                "policy_key": "ariel_teach",
                "status": ToolStatus.ACTIVE,
            },
            {
                "tool_key": ToolKey.STRUCTURED_WHITEBOARD,
                "display_name": "Structured Whiteboard",
                "description": "Open or resume a structured whiteboard",
                "category": "LEARNING",
                "provider_context": ProviderContext.WHITEBOARD,
                "required_capability": "",
                "supported_workspace_types": [],
                "policy_key": "whiteboard_open",
                "status": ToolStatus.ACTIVE,
            },
            {
                "tool_key": ToolKey.RESOURCE_VIEWER,
                "display_name": "Resource Viewer",
                "description": "View governed learning resources",
                "category": "LEARNING",
                "provider_context": ProviderContext.RESOURCE,
                "required_capability": "",
                "supported_workspace_types": [],
                "policy_key": "resource_view",
                "status": ToolStatus.ACTIVE,
            },
            {
                "tool_key": ToolKey.CONCEPT_CHECK,
                "display_name": "Concept Check",
                "description": "Start or resume a concept check",
                "category": "ASSESSMENT",
                "provider_context": ProviderContext.CONCEPT_CHECK,
                "required_capability": "",
                "supported_workspace_types": [],
                "policy_key": "concept_check",
                "status": ToolStatus.ACTIVE,
            },
            {
                "tool_key": ToolKey.LEARNER_NOTES,
                "display_name": "Learner Notes",
                "description": "Create and manage private notes",
                "category": "ORGANIZATION",
                "provider_context": ProviderContext.STUDY_LAB,
                "required_capability": "",
                "supported_workspace_types": [],
                "policy_key": "learner_notes",
                "status": ToolStatus.ACTIVE,
            },
            {
                "tool_key": ToolKey.PROGRESS_VIEW,
                "display_name": "Progress View",
                "description": "View learner-safe progress",
                "category": "REVIEW",
                "provider_context": ProviderContext.PROGRESS,
                "required_capability": "",
                "supported_workspace_types": [],
                "policy_key": "progress_view",
                "status": ToolStatus.ACTIVE,
            },
            {
                "tool_key": ToolKey.JOURNEY_MAP,
                "display_name": "Journey Map",
                "description": "View and navigate the learning journey",
                "category": "ORGANIZATION",
                "provider_context": ProviderContext.JOURNEY,
                "required_capability": "",
                "supported_workspace_types": [],
                "policy_key": "journey_map",
                "status": ToolStatus.ACTIVE,
            },
            {
                "tool_key": ToolKey.RESUME_SESSION,
                "display_name": "Resume Session",
                "description": "Resume the last active session",
                "category": "ORGANIZATION",
                "provider_context": ProviderContext.STUDY_LAB,
                "required_capability": "",
                "supported_workspace_types": [],
                "policy_key": "resume_session",
                "status": ToolStatus.ACTIVE,
            },
        ]

        for tool_data in tools:
            StudyToolDefinition.objects.update_or_create(
                tool_key=tool_data["tool_key"],
                defaults=tool_data,
            )

        return {"panels": len(panels), "tools": len(tools)}


# ============================================================================
# Query Services
# ============================================================================

class ListLearnerStudyWorkspacesQuery:
    @staticmethod
    def execute(learner_id, status=None, workspace_type=None):
        queryset = StudyWorkspace.objects.filter(learner_id=learner_id)
        if status:
            queryset = queryset.filter(status=status)
        if workspace_type:
            queryset = queryset.filter(workspace_type=workspace_type)
        return queryset.order_by("-last_opened_at", "-created_at")


class RetrieveLearnerStudyWorkspaceQuery:
    @staticmethod
    def execute(workspace_id, learner_id):
        workspace = StudyWorkspace.objects.filter(pk=workspace_id, learner_id=learner_id).first()
        if not workspace:
            raise WorkspaceNotFoundError(workspace_id)
        return workspace


class RetrieveActiveStudyWorkspaceQuery:
    @staticmethod
    def execute(learner_id):
        return StudyWorkspace.objects.filter(
            learner_id=learner_id,
            status=WorkspaceStatus.ACTIVE,
        ).order_by("-last_opened_at").first()


class RetrieveWorkspaceAssemblyQuery:
    @staticmethod
    def execute(workspace_id, learner_id):
        return AssembleStudyWorkspaceService.execute(workspace_id, learner_id)


class RetrieveWorkspaceSnapshotQuery:
    @staticmethod
    def execute(workspace_id, learner_id, snapshot_version=None):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        if snapshot_version:
            snapshot = WorkspaceSnapshot.objects.filter(
                workspace=workspace,
                snapshot_version=snapshot_version,
            ).first()
        else:
            snapshot = WorkspaceSnapshot.objects.filter(
                workspace=workspace,
                status=SnapshotStatus.CURRENT,
            ).first()
        if not snapshot:
            raise SnapshotNotAvailableError()
        return snapshot


class ListWorkspacePanelsQuery:
    @staticmethod
    def execute(workspace_id, learner_id):
        return ResolveWorkspacePanelsService.execute(workspace_id, learner_id)


class ListWorkspaceToolsQuery:
    @staticmethod
    def execute(workspace_id, learner_id):
        return ResolveWorkspaceToolAvailabilityService.execute(workspace_id, learner_id)


class RetrieveWorkspaceResumeStateQuery:
    @staticmethod
    def execute(workspace_id, learner_id):
        return ResolveWorkspaceResumeStateService.execute(workspace_id, learner_id)


class ListLearnerWorkspaceNotesQuery:
    @staticmethod
    def execute(workspace_id, learner_id, include_deleted=False):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        queryset = LearnerWorkspaceNote.objects.filter(workspace=workspace, learner_id=learner_id)
        if not include_deleted:
            queryset = queryset.exclude(status=NoteStatus.DELETED)
        return queryset.order_by("-updated_at")


class ListLearnerWorkspaceActivityQuery:
    @staticmethod
    def execute(workspace_id, learner_id, limit=100):
        workspace = _get_owned_workspace(workspace_id, learner_id)
        return WorkspaceActivity.objects.filter(
            workspace=workspace,
            learner_id=learner_id,
        ).order_by("-occurred_at")[:limit]


# ============================================================================
# Internal Helpers
# ============================================================================

def _get_owned_workspace(workspace_id, learner_id):
    workspace = StudyWorkspace.objects.filter(pk=workspace_id).first()
    if not workspace:
        raise WorkspaceNotFoundError(workspace_id)
    if workspace.learner_id != learner_id:
        raise WorkspaceAccessDeniedError()
    return workspace


def _publish_event(event):
    """Publish an event through the existing event platform.

    Uses identifier-only payloads. Falls back gracefully if the event
    platform is not configured.
    """
    try:
        from apps.notifications.domain.events import publish_event
        publish_event(event.event_type, event.payload())
    except ImportError:
        # Event platform not available — event is still defined and available
        # for future integration. No data is lost.
        pass
    except Exception:
        # Never let event publishing break the core operation
        pass


def _upsert_availability(workspace, tool, available, reason_code, reason_detail):
    availability, created = WorkspaceToolAvailability.objects.update_or_create(
        workspace=workspace,
        tool_definition=tool,
        defaults={
            "available": available,
            "reason_code": reason_code,
            "reason_detail": reason_detail[:280],
            "source_versions": {},
            "version": 1,
        },
    )
    return availability
