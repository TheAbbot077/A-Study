from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SynchronizationStatus(StrEnum):
    PLANNED = "planned"
    SYNCHRONIZING = "synchronizing"
    SYNCHRONIZED = "synchronized"
    FAILED = "failed"


class GenerationStatus(StrEnum):
    BUILDING = "building"
    VALIDATING = "validating"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    FAILED = "failed"


@dataclass(frozen=True)
class CitationSpecification:
    source_page_start: int
    source_page_end: int
    semantic_segment_id: str
    source_fingerprint: str
    label: str

    def __post_init__(self):
        if self.source_page_start < 1 or self.source_page_end < self.source_page_start:
            raise ValueError("CITATION_PROVENANCE_MISSING")
        if not self.semantic_segment_id or not self.source_fingerprint:
            raise ValueError("CITATION_PROVENANCE_MISSING")


@dataclass(frozen=True)
class RetrievalChunkSpecification:
    stable_key: str
    resource_id: str
    section_id: str
    concept_id: str | None
    text: str
    ordinal: int
    content_fingerprint: str
    citation: CitationSpecification
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if not self.stable_key or not self.text.strip() or self.ordinal < 1:
            raise ValueError("NO_RETRIEVABLE_CONTENT")


@dataclass(frozen=True)
class RetrievalSynchronizationManifest:
    population_run_id: str
    approved_projection_id: str
    resource_id: str
    subject_id: str
    source_fingerprint: str
    manifest_fingerprint: str
    chunk_policy_version: str
    citation_policy_version: str
    retrieval_schema_version: str
    embedding_version: str
    index_version: str
    chunks: tuple[RetrievalChunkSpecification, ...]


@dataclass(frozen=True)
class SynchronizationReadiness:
    ready: bool
    population_run_id: str
    resource_id: str | None
    source_fingerprint: str
    expected_section_count: int
    expected_concept_count: int
    existing_synchronization_run_id: str | None = None
    active_generation_id: str | None = None
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
