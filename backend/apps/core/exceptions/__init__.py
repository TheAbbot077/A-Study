
from .base import AbbotStudyError


class DomainError(AbbotStudyError):
    """Base class for business-layer failures."""


class DomainValidationError(ValueError, DomainError):
    """Raised when business inputs or invariants are invalid."""


class LifecycleTransitionError(DomainValidationError):
    """Raised when a model or workflow cannot transition to a requested state."""


class RepositoryOperationError(RuntimeError, DomainError):
    """Raised when repository or persistence operations fail predictably."""


__all__ = [
    "AbbotStudyError",
    "DomainError",
    "DomainValidationError",
    "LifecycleTransitionError",
    "RepositoryOperationError",
]
