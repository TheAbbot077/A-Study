import pytest
from apps.retrieval.domain.models import ChunkProjection, RetrievalReadiness
from apps.retrieval.domain.policy import ChunkPolicy, RankingPolicy
from apps.retrieval.domain.queries import RetrievalFilter, RetrievalQuery


def projection(**overrides):
    values = dict(identity_key="identity", text="A stable academic definition.", ordering=1, token_estimate=8, confidence=.9, chunk_type="definition", source_page_start=2, source_page_end=2, institution_id="i", subject_id="s", resource_id="r", section_id="section", concept_id="concept", semantic_segment_id="segment", proposal_id="proposal", proposal_version="p1", population_version="pop1", chunk_policy_version="cp1", retrieval_version="r1", embedding_version="e1", checksum="checksum")
    values.update(overrides); return ChunkProjection(**values)


def test_chunk_identity_and_traceability_are_immutable():
    chunk = projection()
    assert chunk.identity_key == "identity"
    assert chunk.semantic_segment_id == "segment"
    with pytest.raises(Exception):
        chunk.ordering = 2


def test_chunk_invariants_reject_invalid_pages_and_confidence():
    with pytest.raises(ValueError): projection(source_page_start=4, source_page_end=2)
    with pytest.raises(ValueError): projection(confidence=1.1)


def test_policy_and_query_validate_configuration():
    assert ChunkPolicy().estimate_tokens("abcd") == 1
    assert RankingPolicy().vector_weight + RankingPolicy().keyword_weight == 1
    assert RetrievalQuery("cell membrane", RetrievalFilter(subject_id="s")).limit == 8
    with pytest.raises(ValueError): ChunkPolicy(minimum_chunk_size=400, preferred_chunk_size=200)


def test_readiness_lifecycle_has_canonical_states():
    assert {item.value for item in RetrievalReadiness} == {"not_indexed", "indexing", "indexed", "stale", "failed"}

