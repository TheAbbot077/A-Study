from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkPolicy:
    preferred_chunk_size: int = 320
    maximum_chunk_size: int = 640
    minimum_chunk_size: int = 24
    chunk_overlap: int = 32
    token_estimator: str = "characters_divided_by_four"
    citation_policy: str = "source_pages_required"
    metadata_policy: str = "full_academic_provenance"
    ranking_policy: str = "hybrid_v1"
    configuration_version: str = "retrieval-chunk-policy-v1"

    def __post_init__(self) -> None:
        if not 0 < self.minimum_chunk_size <= self.preferred_chunk_size <= self.maximum_chunk_size:
            raise ValueError("Chunk size configuration is invalid.")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.maximum_chunk_size:
            raise ValueError("Chunk overlap configuration is invalid.")

    def estimate_tokens(self, text: str) -> int:
        return max(1, (len(text) + 3) // 4)


@dataclass(frozen=True)
class RankingPolicy:
    vector_weight: float = 0.65
    keyword_weight: float = 0.35
    configuration_version: str = "hybrid-ranking-v1"

    def __post_init__(self) -> None:
        if self.vector_weight < 0 or self.keyword_weight < 0 or abs(self.vector_weight + self.keyword_weight - 1) > 0.0001:
            raise ValueError("Ranking weights must be non-negative and total one.")

