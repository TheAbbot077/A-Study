"""
Study Lab domain exceptions.

All exceptions extend Django ValidationError to integrate with existing
project validation patterns.
"""

from django.core.exceptions import ValidationError


class StudyLabError(ValidationError):
    """Base exception for Study Lab domain errors."""

    def __init__(self, message, code="STUDY_LAB_ERROR", **kwargs):
        super().__init__(message, code=code, **kwargs)


class WorkspaceNotFoundError(StudyLabError):
    def __init__(self, workspace_id=None):
        super().__init__(
            f"Workspace {workspace_id} not found." if workspace_id else "Workspace not found.",
            code="WORKSPACE_NOT_FOUND",
        )


class WorkspaceAccessDeniedError(StudyLabError):
    def __init__(self):
        super().__init__("Access to this workspace is denied.", code="WORKSPACE_ACCESS_DENIED")


class WorkspaceTenantMismatchError(StudyLabError):
    def __init__(self):
        super().__init__("Workspace tenant does not match learner's institution.", code="WORKSPACE_TENANT_MISMATCH")


class WorkspaceInvalidTransitionError(StudyLabError):
    def __init__(self, source, target):
        super().__init__(
            f"Invalid workspace transition: {source} -> {target}.",
            code="WORKSPACE_INVALID_TRANSITION",
        )


class WorkspaceNotActiveError(StudyLabError):
    def __init__(self):
        super().__init__("Workspace is not active.", code="WORKSPACE_NOT_ACTIVE")


class WorkspaceSuspendedError(StudyLabError):
    def __init__(self):
        super().__init__("Workspace is suspended.", code="WORKSPACE_SUSPENDED")


class WorkspaceArchivedError(StudyLabError):
    def __init__(self):
        super().__init__("Workspace is archived and immutable.", code="WORKSPACE_ARCHIVED")


class ContextNotAccessibleError(StudyLabError):
    def __init__(self, context_type="context"):
        super().__init__(f"Referenced {context_type} is not accessible.", code="CONTEXT_NOT_ACCESSIBLE")


class ContextMismatchError(StudyLabError):
    def __init__(self):
        super().__init__("Referenced context does not match workspace tenant.", code="CONTEXT_MISMATCH")


class ToolNotFoundError(StudyLabError):
    def __init__(self, tool_key=None):
        super().__init__(
            f"Tool {tool_key} not found." if tool_key else "Tool not found.",
            code="TOOL_NOT_FOUND",
        )


class ToolUnavailableError(StudyLabError):
    def __init__(self, reason_code="TOOL_UNAVAILABLE", reason_detail=""):
        super().__init__(
            f"Tool is unavailable: {reason_detail}" if reason_detail else "Tool is unavailable.",
            code=reason_code,
        )


class ToolCapabilityRequiredError(StudyLabError):
    def __init__(self, capability_code=""):
        super().__init__(
            f"Capability required: {capability_code}" if capability_code else "Capability required.",
            code="TOOL_CAPABILITY_REQUIRED",
        )


class ToolProviderUnavailableError(StudyLabError):
    def __init__(self, provider=""):
        super().__init__(
            f"Provider unavailable: {provider}" if provider else "Provider unavailable.",
            code="TOOL_PROVIDER_UNAVAILABLE",
        )


class ToolInvocationFailedError(StudyLabError):
    def __init__(self, reason=""):
        super().__init__(
            f"Tool invocation failed: {reason}" if reason else "Tool invocation failed.",
            code="TOOL_INVOCATION_FAILED",
        )


class ToolSessionNotFoundError(StudyLabError):
    def __init__(self, session_id=None):
        super().__init__(
            f"Tool session {session_id} not found." if session_id else "Tool session not found.",
            code="TOOL_SESSION_NOT_FOUND",
        )


class ToolSessionAccessDeniedError(StudyLabError):
    def __init__(self):
        super().__init__("Access to this tool session is denied.", code="TOOL_SESSION_ACCESS_DENIED")


class ToolSessionNotResumableError(StudyLabError):
    def __init__(self):
        super().__init__("Tool session is not resumable.", code="TOOL_SESSION_NOT_RESUMABLE")


class ToolSessionAlreadyOpenError(StudyLabError):
    def __init__(self):
        super().__init__("Tool session is already open.", code="TOOL_SESSION_ALREADY_OPEN")


class ToolSessionAlreadyCompletedError(StudyLabError):
    def __init__(self):
        super().__init__("Tool session is already completed.", code="TOOL_SESSION_ALREADY_COMPLETED")


class ToolSessionFailedError(StudyLabError):
    def __init__(self):
        super().__init__("Tool session failed.", code="TOOL_SESSION_FAILED")


class ToolSessionAbandonedError(StudyLabError):
    def __init__(self):
        super().__init__("Tool session is abandoned.", code="TOOL_SESSION_ABANDONED")


class ToolSessionInvalidTransitionError(StudyLabError):
    def __init__(self):
        super().__init__("Invalid tool session transition.", code="TOOL_SESSION_INVALID_TRANSITION")


class ToolSessionVersionConflictError(StudyLabError):
    def __init__(self):
        super().__init__("Tool session version conflict.", code="TOOL_SESSION_VERSION_CONFLICT")


class ToolProviderTransientFailureError(StudyLabError):
    def __init__(self, reason=""):
        super().__init__(reason or "Tool provider transient failure.", code="TOOL_PROVIDER_TRANSIENT_FAILURE")


class ToolProviderTerminalFailureError(StudyLabError):
    def __init__(self, reason=""):
        super().__init__(reason or "Tool provider terminal failure.", code="TOOL_PROVIDER_TERMINAL_FAILURE")


class ToolSessionTerminalFailureError(StudyLabError):
    def __init__(self, reason=""):
        super().__init__(reason or "Tool session terminal failure.", code="TOOL_SESSION_TERMINAL_FAILURE")


class IdempotencyConflictError(StudyLabError):
    def __init__(self):
        super().__init__("Idempotency conflict.", code="IDEMPOTENCY_CONFLICT")


class ScaffoldGenerationNotFoundError(StudyLabError):
    def __init__(self, request_id=None):
        super().__init__(
            f"Scaffold generation request {request_id} not found." if request_id else "Scaffold generation request not found.",
            code="SCAFFOLD_GENERATION_NOT_FOUND",
        )


class ScaffoldGenerationInvalidTransitionError(StudyLabError):
    def __init__(self):
        super().__init__("Invalid scaffold generation transition.", code="SCAFFOLD_GENERATION_INVALID_TRANSITION")


class ScaffoldGenerationProviderUnavailableError(StudyLabError):
    def __init__(self, provider=""):
        super().__init__(
            f"Scaffold generation provider unavailable: {provider}" if provider else "Scaffold generation provider unavailable.",
            code="SCAFFOLD_PROVIDER_UNAVAILABLE",
        )


class NoteNotFoundError(StudyLabError):
    def __init__(self, note_id=None):
        super().__init__(
            f"Note {note_id} not found." if note_id else "Note not found.",
            code="NOTE_NOT_FOUND",
        )


class NoteAccessDeniedError(StudyLabError):
    def __init__(self):
        super().__init__("Access to this note is denied.", code="NOTE_ACCESS_DENIED")


class NoteVersionConflictError(StudyLabError):
    def __init__(self):
        super().__init__("Version conflict: note was modified by another request.", code="NOTE_VERSION_CONFLICT")


class SnapshotNotAvailableError(StudyLabError):
    def __init__(self):
        super().__init__("No current snapshot is available.", code="SNAPSHOT_NOT_AVAILABLE")


class AssemblyProviderFailureError(StudyLabError):
    def __init__(self, provider=""):
        super().__init__(
            f"Provider failure during assembly: {provider}" if provider else "Provider failure during assembly.",
            code="ASSEMBLY_PROVIDER_FAILURE",
        )


class ArtefactNotFoundError(StudyLabError):
    def __init__(self, artefact_id=None):
        super().__init__(f"Artefact {artefact_id} not found." if artefact_id else "Artefact not found.", code="ARTEFACT_NOT_FOUND")


class ArtefactAccessDeniedError(StudyLabError):
    def __init__(self):
        super().__init__("Access to this artefact is denied.", code="ARTEFACT_ACCESS_DENIED")


class ArtefactArchivedError(StudyLabError):
    def __init__(self):
        super().__init__("Artefact is archived.", code="ARTEFACT_ARCHIVED")


class ArtefactVersionConflictError(StudyLabError):
    def __init__(self):
        super().__init__("Version conflict: artefact was modified by another request.", code="ARTEFACT_VERSION_CONFLICT")


class TransformationRequestNotFoundError(StudyLabError):
    def __init__(self, request_id=None):
        super().__init__(f"Transformation request {request_id} not found." if request_id else "Transformation request not found.", code="TRANSFORMATION_NOT_FOUND")
