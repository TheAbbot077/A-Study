from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AttributeProvenanceResult:
    attribute_id: str
    classification: str
    status: str
    reason_codes: list[str]
    active_evidence_count: int
    authoritative_evidence_count: int
    contradiction_count: int
    stale_evidence_count: int


@dataclass(frozen=True)
class ProfileVersionProvenanceReadiness:
    profile_version_id: str
    status: str
    attribute_results: list[AttributeProvenanceResult]
    blocking_codes: list[str]
    review_codes: list[str]
    evaluated_at: datetime


@dataclass(frozen=True)
class EvidenceLinkSummary:
    evidence_link_id: str
    attribute_id: str
    attribute_type: str
    classification: str
    source_domain: str
    source_type: str
    relationship: str
    authority_class: str
    status: str
    safe_summary: str
    review_required: bool
    reason_codes: list[str]

