class ContentIntelligenceError(Exception):
    """Base content intelligence error."""


class UnsupportedFormatError(ValueError, ContentIntelligenceError):
    """Raised when an import format is unsupported."""


class ImportLifecycleError(ValueError, ContentIntelligenceError):
    """Raised when an import job or pipeline run receives an invalid transition."""


class ExtractionError(ContentIntelligenceError):
    """Raised when extraction fails."""

    def __init__(self, message: str, *, code: str = "extraction_failed", details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ContentImportDeletionError(ContentIntelligenceError):
    """Raised when an import deletion cannot be completed safely."""

    def __init__(self, message: str, *, code: str = "deletion_failed", details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ContentImportDeletionConflictError(ContentImportDeletionError):
    """Raised when an import is not deletable in its current lifecycle state."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message, code="deletion_conflict", details=details)
