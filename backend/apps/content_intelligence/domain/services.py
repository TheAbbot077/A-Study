from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExtractionPayload:
    extracted_text: str
    normalized_text: str
    extraction_method: str
    sufficient_text: bool
    page_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SectionCandidate:
    heading: str
    body_text: str
    sequence_number: int
    section_type: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConceptCandidateData:
    title: str
    description: str
    learning_objective: str
    sequence_number: int
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationFindingData:
    severity: str
    finding_type: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentNormalizationResult:
    normalized_text: str
    cleaned_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HeadingNormalizationResult:
    original_heading: str
    normalized_heading: str
    structural_prefix: str = ""
    sequence_number: int | None = None
    semantic_title: str = ""
    generic_structure: bool = False
    malformed_tokenization: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConceptCandidateAssessment:
    normalized_title: str
    confidence: float
    decision: str
    rejection_reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
