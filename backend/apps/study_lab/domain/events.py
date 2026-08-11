"""
Study Lab domain events. Identifier-only payloads. Idempotent.

Event payloads contain only identifiers and safe metadata.
No note content, transcripts, Ariel memory, learner explanations,
assessment answers, or hidden prompts.
"""


class StudyWorkspaceCreated:
    event_type = "study_lab.workspace.created"
    version = 1

    def __init__(self, workspace_id, learner_id, tenant_id=None, workspace_type=""):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.tenant_id = tenant_id
        self.workspace_type = workspace_type

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "workspace_type": self.workspace_type,
        }


class StudyWorkspaceActivated:
    event_type = "study_lab.workspace.activated"
    version = 1

    def __init__(self, workspace_id, learner_id):
        self.workspace_id = workspace_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
        }


class StudyWorkspacePaused:
    event_type = "study_lab.workspace.paused"
    version = 1

    def __init__(self, workspace_id, learner_id):
        self.workspace_id = workspace_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
        }


class StudyWorkspaceResumed:
    event_type = "study_lab.workspace.resumed"
    version = 1

    def __init__(self, workspace_id, learner_id):
        self.workspace_id = workspace_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
        }


class StudyWorkspaceSuspended:
    event_type = "study_lab.workspace.suspended"
    version = 1

    def __init__(self, workspace_id, learner_id):
        self.workspace_id = workspace_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
        }


class StudyWorkspaceRestored:
    event_type = "study_lab.workspace.restored"
    version = 1

    def __init__(self, workspace_id, learner_id):
        self.workspace_id = workspace_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
        }


class StudyWorkspaceCompleted:
    event_type = "study_lab.workspace.completed"
    version = 1

    def __init__(self, workspace_id, learner_id):
        self.workspace_id = workspace_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
        }


class StudyWorkspaceArchived:
    event_type = "study_lab.workspace.archived"
    version = 1

    def __init__(self, workspace_id, learner_id):
        self.workspace_id = workspace_id
        self.learner_id = learner_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
        }


class WorkspaceContextChanged:
    event_type = "study_lab.workspace.context_changed"
    version = 1

    def __init__(self, workspace_id, learner_id, context_version=1):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.context_version = context_version

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "context_version": self.context_version,
        }


class WorkspaceResumePointUpdated:
    event_type = "study_lab.workspace.resume_point_updated"
    version = 1

    def __init__(self, workspace_id, learner_id, resume_version=1):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.resume_version = resume_version

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "resume_version": self.resume_version,
        }


class WorkspaceSnapshotCreated:
    event_type = "study_lab.workspace.snapshot_created"
    version = 1

    def __init__(self, workspace_id, learner_id, snapshot_version=1):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.snapshot_version = snapshot_version

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "snapshot_version": self.snapshot_version,
        }


class WorkspaceSnapshotMarkedStale:
    event_type = "study_lab.workspace.snapshot_marked_stale"
    version = 1

    def __init__(self, workspace_id, learner_id, snapshot_version=1):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.snapshot_version = snapshot_version

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "snapshot_version": self.snapshot_version,
        }


class WorkspaceToolInvoked:
    event_type = "study_lab.workspace.tool_invoked"
    version = 1

    def __init__(self, workspace_id, learner_id, tool_key="", invocation_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.tool_key = tool_key
        self.invocation_id = invocation_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "tool_key": self.tool_key,
            "invocation_id": str(self.invocation_id) if self.invocation_id else None,
        }


class WorkspaceToolInvocationRejected:
    event_type = "study_lab.workspace.tool_invocation_rejected"
    version = 1

    def __init__(self, workspace_id, learner_id, tool_key="", reason_code=""):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.tool_key = tool_key
        self.reason_code = reason_code

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "tool_key": self.tool_key,
            "reason_code": self.reason_code,
        }


class LearnerWorkspaceNoteCreated:
    event_type = "study_lab.note.created"
    version = 1

    def __init__(self, workspace_id, learner_id, note_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.note_id = note_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "note_id": str(self.note_id) if self.note_id else None,
        }


class LearnerWorkspaceNoteUpdated:
    event_type = "study_lab.note.updated"
    version = 1

    def __init__(self, workspace_id, learner_id, note_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.note_id = note_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "note_id": str(self.note_id) if self.note_id else None,
        }


class LearnerWorkspaceNoteArchived:
    event_type = "study_lab.note.archived"
    version = 1

    def __init__(self, workspace_id, learner_id, note_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.note_id = note_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "note_id": str(self.note_id) if self.note_id else None,
        }


class LearnerWorkspaceNoteDeleted:
    event_type = "study_lab.note.deleted"
    version = 1

    def __init__(self, workspace_id, learner_id, note_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.note_id = note_id

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "note_id": str(self.note_id) if self.note_id else None,
        }


class StudyToolLaunched:
    event_type = "study_lab.tool.launched"
    version = 1

    def __init__(self, workspace_id, learner_id, tool_key="", invocation_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.tool_key = tool_key
        self.invocation_id = invocation_id

    def payload(self):
        return {"workspace_id": str(self.workspace_id), "learner_id": str(self.learner_id), "tool_key": self.tool_key, "invocation_id": str(self.invocation_id) if self.invocation_id else None}


class StudyToolSessionOpened:
    event_type = "study_lab.tool_session.opened"
    version = 1

    def __init__(self, workspace_id, learner_id, session_id=None, tool_key=""):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.session_id = session_id
        self.tool_key = tool_key

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "session_id": str(self.session_id) if self.session_id else None,
            "tool_key": self.tool_key,
        }


class StudyToolSessionSuspended:
    event_type = "study_lab.tool_session.suspended"
    version = 1

    def __init__(self, workspace_id, learner_id, session_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.session_id = session_id

    def payload(self):
        return {"workspace_id": str(self.workspace_id), "learner_id": str(self.learner_id), "session_id": str(self.session_id) if self.session_id else None}


class StudyToolSessionResumed(StudyToolSessionSuspended):
    event_type = "study_lab.tool_session.resumed"


class StudyToolSessionCompleted(StudyToolSessionSuspended):
    event_type = "study_lab.tool_session.completed"


class StudyToolSessionFailed(StudyToolSessionSuspended):
    event_type = "study_lab.tool_session.failed"


class StudyToolSessionAbandoned(StudyToolSessionSuspended):
    event_type = "study_lab.tool_session.abandoned"


class StudyArtefactCreated:
    event_type = "study_lab.artefact.created"
    version = 1

    def __init__(self, workspace_id, learner_id, artefact_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.artefact_id = artefact_id

    def payload(self):
        return {"workspace_id": str(self.workspace_id), "learner_id": str(self.learner_id), "artefact_id": str(self.artefact_id) if self.artefact_id else None}


class StudyArtefactVersioned:
    event_type = "study_lab.artefact.versioned"
    version = 1

    def __init__(self, workspace_id, learner_id, artefact_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.artefact_id = artefact_id

    def payload(self):
        return {"workspace_id": str(self.workspace_id), "learner_id": str(self.learner_id), "artefact_id": str(self.artefact_id) if self.artefact_id else None}


class StudyArtefactArchived:
    event_type = "study_lab.artefact.archived"
    version = 1

    def __init__(self, workspace_id, learner_id, artefact_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.artefact_id = artefact_id

    def payload(self):
        return {"workspace_id": str(self.workspace_id), "learner_id": str(self.learner_id), "artefact_id": str(self.artefact_id) if self.artefact_id else None}


class StudyArtefactImported(StudyArtefactCreated):
    event_type = "study_lab.artefact.imported"


class StudyArtefactExported:
    event_type = "study_lab.artefact.exported"
    version = 1

    def __init__(self, workspace_id, learner_id, artefact_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.artefact_id = artefact_id

    def payload(self):
        return {"workspace_id": str(self.workspace_id), "learner_id": str(self.learner_id), "artefact_id": str(self.artefact_id) if self.artefact_id else None}


class StudyArtefactShared(StudyArtefactExported):
    event_type = "study_lab.artefact.shared"


class StudyTransformationRequested:
    event_type = "study_lab.transformation.requested"
    version = 1

    def __init__(self, workspace_id, learner_id, request_id=None):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.request_id = request_id

    def payload(self):
        return {"workspace_id": str(self.workspace_id), "learner_id": str(self.learner_id), "request_id": str(self.request_id) if self.request_id else None}


class StudyTransformationCompleted(StudyTransformationRequested):
    event_type = "study_lab.transformation.completed"


class StudyTransformationFailed(StudyTransformationRequested):
    event_type = "study_lab.transformation.failed"


class StudyScaffoldGenerationRequested:
    event_type = "study_lab.scaffold_generation.requested"
    version = 1

    def __init__(self, workspace_id, learner_id, request_id=None, generation_type=""):
        self.workspace_id = workspace_id
        self.learner_id = learner_id
        self.request_id = request_id
        self.generation_type = generation_type

    def payload(self):
        return {
            "workspace_id": str(self.workspace_id),
            "learner_id": str(self.learner_id),
            "request_id": str(self.request_id) if self.request_id else None,
            "generation_type": self.generation_type,
        }


class StudyScaffoldGenerationStarted(StudyScaffoldGenerationRequested):
    event_type = "study_lab.scaffold_generation.started"


class StudyScaffoldGenerationCompleted(StudyScaffoldGenerationRequested):
    event_type = "study_lab.scaffold_generation.completed"

    def __init__(self, workspace_id, learner_id, request_id=None, generation_type="", artefact_id=None):
        super().__init__(workspace_id, learner_id, request_id=request_id, generation_type=generation_type)
        self.artefact_id = artefact_id

    def payload(self):
        payload = super().payload()
        payload["artefact_id"] = str(self.artefact_id) if self.artefact_id else None
        return payload


class StudyScaffoldGenerationFailed(StudyScaffoldGenerationRequested):
    event_type = "study_lab.scaffold_generation.failed"

    def __init__(self, workspace_id, learner_id, request_id=None, generation_type="", reason_code=""):
        super().__init__(workspace_id, learner_id, request_id=request_id, generation_type=generation_type)
        self.reason_code = reason_code

    def payload(self):
        payload = super().payload()
        payload["reason_code"] = self.reason_code
        return payload


class StudyScaffoldGenerationCancelled(StudyScaffoldGenerationRequested):
    event_type = "study_lab.scaffold_generation.cancelled"
