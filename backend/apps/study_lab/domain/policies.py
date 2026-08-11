"""
Study Lab domain policies.

Lifecycle transition rules and workspace ownership rules.
"""

from __future__ import annotations

from .enums import WorkspaceStatus


class WorkspaceLifecyclePolicy:
    """Defines valid workspace lifecycle transitions."""

    ALLOWED_TRANSITIONS = {
        WorkspaceStatus.DRAFT: {
            WorkspaceStatus.ACTIVE,
            WorkspaceStatus.ARCHIVED,
        },
        WorkspaceStatus.ACTIVE: {
            WorkspaceStatus.PAUSED,
            WorkspaceStatus.SUSPENDED,
            WorkspaceStatus.COMPLETED,
            WorkspaceStatus.ARCHIVED,
        },
        WorkspaceStatus.PAUSED: {
            WorkspaceStatus.ACTIVE,
            WorkspaceStatus.SUSPENDED,
            WorkspaceStatus.ARCHIVED,
        },
        WorkspaceStatus.SUSPENDED: {
            WorkspaceStatus.ACTIVE,
            WorkspaceStatus.PAUSED,
            WorkspaceStatus.ARCHIVED,
        },
        WorkspaceStatus.COMPLETED: {
            WorkspaceStatus.ACTIVE,
            WorkspaceStatus.ARCHIVED,
        },
        WorkspaceStatus.ARCHIVED: set(),
    }

    @classmethod
    def can_transition(cls, source: str, target: str) -> bool:
        return target in cls.ALLOWED_TRANSITIONS.get(source, set())

    @classmethod
    def validate(cls, source: str, target: str) -> None:
        if not cls.can_transition(source, target):
            from .exceptions import WorkspaceInvalidTransitionError
            raise WorkspaceInvalidTransitionError(source, target)

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return status == WorkspaceStatus.ARCHIVED

    @classmethod
    def is_mutable(cls, status: str) -> bool:
        return status not in {WorkspaceStatus.ARCHIVED}

    @classmethod
    def can_reopen_completed(cls) -> bool:
        """Policy: completed workspaces may be reopened to ACTIVE."""
        return True
