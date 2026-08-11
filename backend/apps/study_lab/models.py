"""
Study Lab models discovery bridge.

Django models live in domain/models.py. This module re-exports them
so Django's app registry and admin can discover them.
"""

from apps.study_lab.domain.models import (  # noqa: F401
    ArtefactTransformationRequest,
    LearnerWorkspaceNote,
    StudyArtefact,
    StudyArtefactLineage,
    StudyArtefactTransformationDefinition,
    StudyToolDefinition,
    StudyToolManifest,
    StudyWorkspace,
    WorkspaceActivity,
    WorkspaceContext,
    WorkspacePanelDefinition,
    WorkspaceResumeState,
    WorkspaceSnapshot,
    WorkspaceToolAvailability,
    WorkspaceToolInvocation,
    WorkspaceToolSession,
)
