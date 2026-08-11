"""
Study Lab capability codes.

Capabilities represent fine-grained educational authority for the Study Lab.
Learner capabilities are self-granted. Administrative permissions do NOT
imply private-content access.
"""


class StudyLabCapability:
    """Study Lab capability codes."""

    # Learner capabilities
    STUDY_LAB_USE = "study_lab.use"
    STUDY_WORKSPACE_CREATE = "study_workspace.create"
    STUDY_WORKSPACE_VIEW_OWN = "study_workspace.view_own"
    STUDY_WORKSPACE_UPDATE_OWN = "study_workspace.update_own"
    STUDY_WORKSPACE_ACTIVATE_OWN = "study_workspace.activate_own"
    STUDY_WORKSPACE_PAUSE_OWN = "study_workspace.pause_own"
    STUDY_WORKSPACE_RESUME_OWN = "study_workspace.resume_own"
    STUDY_WORKSPACE_COMPLETE_OWN = "study_workspace.complete_own"
    STUDY_WORKSPACE_ARCHIVE_OWN = "study_workspace.archive_own"
    STUDY_TOOL_USE = "study_tool.use"
    STUDY_NOTE_CREATE_OWN = "study_note.create_own"
    STUDY_NOTE_VIEW_OWN = "study_note.view_own"
    STUDY_NOTE_UPDATE_OWN = "study_note.update_own"
    STUDY_NOTE_DELETE_OWN = "study_note.delete_own"

    # Administrative capabilities (do NOT imply private-content access)
    STUDY_LAB_ADMIN_VIEW_STATUS = "study_lab.admin_view_status"
    STUDY_LAB_ADMIN_SUSPEND = "study_lab.admin_suspend"
    STUDY_LAB_ADMIN_RESTORE = "study_lab.admin_restore"
    STUDY_LAB_ADMIN_VIEW_AUDIT = "study_lab.admin_view_audit"

    @classmethod
    def get_learner_bundle(cls):
        """Return the default capability bundle for a learner."""
        return [
            cls.STUDY_LAB_USE,
            cls.STUDY_WORKSPACE_CREATE,
            cls.STUDY_WORKSPACE_VIEW_OWN,
            cls.STUDY_WORKSPACE_UPDATE_OWN,
            cls.STUDY_WORKSPACE_ACTIVATE_OWN,
            cls.STUDY_WORKSPACE_PAUSE_OWN,
            cls.STUDY_WORKSPACE_RESUME_OWN,
            cls.STUDY_WORKSPACE_COMPLETE_OWN,
            cls.STUDY_WORKSPACE_ARCHIVE_OWN,
            cls.STUDY_TOOL_USE,
            cls.STUDY_NOTE_CREATE_OWN,
            cls.STUDY_NOTE_VIEW_OWN,
            cls.STUDY_NOTE_UPDATE_OWN,
            cls.STUDY_NOTE_DELETE_OWN,
        ]

    @classmethod
    def get_admin_bundle(cls):
        """Return the capability bundle for a Study Lab administrator.

        Administrative permissions do NOT imply:
        - note access
        - Ariel memory access
        - transcript access
        - private activity access
        """
        return [
            cls.STUDY_LAB_ADMIN_VIEW_STATUS,
            cls.STUDY_LAB_ADMIN_SUSPEND,
            cls.STUDY_LAB_ADMIN_RESTORE,
            cls.STUDY_LAB_ADMIN_VIEW_AUDIT,
        ]

    @classmethod
    def get_all_capabilities(cls):
        """Return all defined capabilities."""
        return [
            cls.STUDY_LAB_USE,
            cls.STUDY_WORKSPACE_CREATE,
            cls.STUDY_WORKSPACE_VIEW_OWN,
            cls.STUDY_WORKSPACE_UPDATE_OWN,
            cls.STUDY_WORKSPACE_ACTIVATE_OWN,
            cls.STUDY_WORKSPACE_PAUSE_OWN,
            cls.STUDY_WORKSPACE_RESUME_OWN,
            cls.STUDY_WORKSPACE_COMPLETE_OWN,
            cls.STUDY_WORKSPACE_ARCHIVE_OWN,
            cls.STUDY_TOOL_USE,
            cls.STUDY_NOTE_CREATE_OWN,
            cls.STUDY_NOTE_VIEW_OWN,
            cls.STUDY_NOTE_UPDATE_OWN,
            cls.STUDY_NOTE_DELETE_OWN,
            cls.STUDY_LAB_ADMIN_VIEW_STATUS,
            cls.STUDY_LAB_ADMIN_SUSPEND,
            cls.STUDY_LAB_ADMIN_RESTORE,
            cls.STUDY_LAB_ADMIN_VIEW_AUDIT,
        ]
