from apps.core.exceptions import LifecycleTransitionError


class ProcessingLifecycleError(LifecycleTransitionError):
    """Raised when a content-processing lifecycle transition is invalid."""


class StaleProcessingAttemptError(ProcessingLifecycleError):
    """Raised when a stale or superseded attempt tries to mutate a job."""

