from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from apps.content_processing.domain.extraction import SourceFormat


@dataclass(frozen=True)
class SourceDocument:
    stored_file_id: str
    filename: str
    declared_content_type: str
    size_bytes: int
    checksum: str
    content: bytes


@dataclass(frozen=True)
class InspectionEvidence:
    detected_format: str
    detected_mime_type: str
    page_count: int | None
    encrypted: bool = False
    password_required: bool = False
    corrupt: bool = False
    native_text_available: bool = False
    native_text_quality: str = "unresolved"
    text_classification: str = "empty_or_unresolved"
    ocr_requirement: str = "not_required"
    ocr_pages_recommended: tuple[int, ...] = ()
    parser_recommendation: str = ""
    confidence: float = 0
    warnings: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class BlockEvidence:
    sequence_number: int
    page_sequence_number: int
    block_type: str
    evidence_origin: str
    raw_text: str = ""
    normalized_text: str = ""
    page_reference: dict[str, object] = field(default_factory=dict)
    geometry: dict[str, object] = field(default_factory=dict)
    typography: dict[str, object] = field(default_factory=dict)
    structural_hints: dict[str, object] = field(default_factory=dict)
    source_method: str = ""
    table_reference: str = ""
    image_reference: str = ""
    confidence: float = 0
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionEvidence:
    method: str
    blocks: tuple[BlockEvidence, ...]
    page_count: int | None
    native_text_pages: int = 0
    ocr_pages: int = 0
    ocr_engine: str = ""
    ocr_engine_version: str = ""
    warnings: tuple[dict[str, object], ...] = ()


class SourceDocumentReader(Protocol):
    def read(self, stored_file_id: str) -> SourceDocument: ...


class DocumentInspector(Protocol):
    name: str
    version: str
    def supports(self, detected_format: SourceFormat) -> bool: ...
    def inspect(self, source: SourceDocument) -> InspectionEvidence: ...


class DocumentExtractor(Protocol):
    name: str
    version: str
    def supports(self, detected_format: SourceFormat) -> bool: ...
    def extract(self, source: SourceDocument, profile) -> ExtractionEvidence: ...


class OcrProvider(Protocol):
    name: str
    version: str
    def is_available(self) -> bool: ...
    def extract_page(self, image, page_number: int) -> tuple[BlockEvidence, ...]: ...
