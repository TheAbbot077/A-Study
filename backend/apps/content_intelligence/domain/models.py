from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from django.utils import timezone

from apps.content_intelligence.domain.exceptions import ImportLifecycleError


@dataclass
class ContentImportJob:
    class Status:
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"

    class FormatType:
        PDF = "pdf"
        DOCX = "docx"

    learning_resource: Any
    format_type: str
    stored_file: Any | None = None
    requested_by: Any | None = None
    status: str = Status.PENDING
    error_message: str = ""
    ocr_requested: bool = False
    ocr_used: bool = False
    extraction_confidence: float | None = None
    section_confidence: float | None = None
    concept_confidence: float | None = None
    structural_confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: Any | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def learning_resource_id(self) -> Any | None:
        return getattr(self.learning_resource, "id", None)

    @property
    def stored_file_id(self) -> Any | None:
        return getattr(self.stored_file, "id", None)

    def start(self) -> None:
        if self.status not in {self.Status.PENDING, self.Status.PROCESSING}:
            raise ImportLifecycleError(f"Cannot start content import job from {self.status}.")
        self.status = self.Status.PROCESSING
        self.started_at = self.started_at or timezone.now()

    def complete(self) -> None:
        if self.status not in {self.Status.PROCESSING, self.Status.PENDING}:
            raise ImportLifecycleError(f"Cannot complete content import job from {self.status}.")
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.error_message = ""

    def fail(self, error_message: str) -> None:
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()

    def cancel(self) -> None:
        if self.status == self.Status.COMPLETED:
            raise ImportLifecycleError("Cannot cancel a completed content import job.")
        self.status = self.Status.CANCELLED
        self.completed_at = timezone.now()

    def mark_ocr_requested(self) -> None:
        self.ocr_requested = True

    def mark_ocr_completed(self) -> None:
        self.ocr_used = True


@dataclass
class ParsedDocument:
    import_job: Any
    title: str = ""
    normalized_text: str = ""
    format_type: str = ContentImportJob.FormatType.PDF
    extraction_method: str = ""
    page_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: Any | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def import_job_id(self) -> Any | None:
        return getattr(self.import_job, "id", None)


@dataclass
class ParsedSection:
    class SectionType:
        FRONT_MATTER = "front_matter"
        CHAPTER = "chapter"
        APPENDIX = "appendix"
        UNKNOWN = "unknown"

    heading: str
    sequence_number: int
    parsed_document: Any | None = None
    body_text: str = ""
    section_type: str = SectionType.UNKNOWN
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    concept_candidates: list[Any] = field(default_factory=list)
    id: Any | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def parsed_document_id(self) -> Any | None:
        return getattr(self.parsed_document, "id", None)


@dataclass
class ParsedConceptCandidate:
    title: str
    sequence_number: int
    parsed_section: Any | None = None
    description: str = ""
    learning_objective: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    id: Any | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def parsed_section_id(self) -> Any | None:
        return getattr(self.parsed_section, "id", None)


@dataclass
class ContentExtractionResult:
    import_job: Any | None = None
    extracted_text: str = ""
    normalized_text: str = ""
    extraction_method: str = ""
    sufficient_text: bool = False
    ocr_requested: bool = False
    ocr_used: bool = False
    char_count: int = 0
    page_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: Any | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def import_job_id(self) -> Any | None:
        return getattr(self.import_job, "id", None)


@dataclass
class ContentValidationFinding:
    class Severity:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

    import_job: Any | None = None
    severity: str = Severity.MEDIUM
    finding_type: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    id: Any | None = None
    created_at: datetime | None = None

    @property
    def import_job_id(self) -> Any | None:
        return getattr(self.import_job, "id", None)


@dataclass
class ParserPipelineRun:
    class Status:
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"

    import_job: Any
    status: str = Status.PENDING
    current_stage: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    id: Any | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def import_job_id(self) -> Any | None:
        return getattr(self.import_job, "id", None)

    def start(self, stage: str) -> None:
        self.status = self.Status.RUNNING
        self.current_stage = stage
        self.started_at = self.started_at or timezone.now()

    def advance(self, stage: str) -> None:
        if self.status != self.Status.RUNNING:
            raise ImportLifecycleError(f"Cannot advance pipeline run from {self.status}.")
        self.current_stage = stage

    def complete(self) -> None:
        if self.status not in {self.Status.RUNNING, self.Status.PENDING}:
            raise ImportLifecycleError(f"Cannot complete pipeline run from {self.status}.")
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()

    def fail(self, error_message: str) -> None:
        self.status = self.Status.FAILED
        self.completed_at = timezone.now()
        metadata = dict(self.metadata or {})
        metadata["error_message"] = error_message
        self.metadata = metadata


__all__ = [
    "ContentImportJob",
    "ParsedDocument",
    "ParsedSection",
    "ParsedConceptCandidate",
    "ContentExtractionResult",
    "ContentValidationFinding",
    "ParserPipelineRun",
]
