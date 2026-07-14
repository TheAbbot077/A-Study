from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RetrievalReadiness(StrEnum):
    NOT_INDEXED = "not_indexed"
    INDEXING = "indexing"
    INDEXED = "indexed"
    STALE = "stale"
    FAILED = "failed"


@dataclass(frozen=True)
class ChunkProjection:
    identity_key: str
    text: str
    ordering: int
    token_estimate: int
    confidence: float
    chunk_type: str
    source_page_start: int
    source_page_end: int
    institution_id: str
    subject_id: str
    resource_id: str
    section_id: str
    concept_id: str | None
    semantic_segment_id: str | None
    proposal_id: str
    proposal_version: str
    population_version: str
    chunk_policy_version: str
    retrieval_version: str
    embedding_version: str
    checksum: str
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text.strip() or self.ordering < 1 or self.token_estimate < 1:
            raise ValueError("Retrieval chunks require normalized text and stable positive ordering.")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Retrieval chunk confidence must be bounded.")
        if self.source_page_start < 1 or self.source_page_end < self.source_page_start:
            raise ValueError("Retrieval chunks require valid source pages.")


@dataclass(frozen=True)
class CitationTrace:
    chunk_id: str
    institution_id: str
    subject_id: str
    resource_id: str
    section_id: str
    concept_id: str | None
    semantic_segment_id: str | None
    proposal_id: str
    population_job_id: str
    source_page_start: int
    source_page_end: int


@dataclass(frozen=True)
class RetrievalStatistics:
    candidate_count: int = 0
    returned_count: int = 0
    tokens_used: int = 0
    vector_weight: float = 0.0
    keyword_weight: float = 0.0


@dataclass(frozen=True)
class RetrievalDiagnostic:
    code: str
    severity: str
    message: str
    details: dict[str, object] = field(default_factory=dict)

