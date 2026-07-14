from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalFilter:
    institution_id: str | None = None
    subject_id: str | None = None
    resource_id: str | None = None
    section_id: str | None = None
    concept_id: str | None = None
    proposal_version: str | None = None
    population_version: str | None = None
    source_page_start: int | None = None
    source_page_end: int | None = None
    chunk_type: str | None = None


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    filters: RetrievalFilter = field(default_factory=RetrievalFilter)
    limit: int = 8
    token_budget: int = 1800

    def __post_init__(self) -> None:
        if not self.text.strip() or self.limit < 1 or self.token_budget < 1:
            raise ValueError("A retrieval query requires text and positive limits.")


@dataclass(frozen=True)
class RetrievalRanking:
    vector_score: float
    keyword_score: float
    final_score: float
    policy_version: str


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    text: str
    token_estimate: int
    metadata: dict[str, object]
    ranking: RetrievalRanking

