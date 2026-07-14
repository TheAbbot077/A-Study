import pytest
from apps.retrieval.infrastructure.embedding import DeterministicEmbeddingProvider, EmbeddingProviderRegistry, EmbeddingProviderUnavailable
from apps.retrieval.infrastructure.indexes import _cosine, _keyword


def test_embedding_is_deterministic_versioned_and_batched():
    provider = DeterministicEmbeddingProvider()
    assert provider.embed("mitosis cell") == provider.embed_batch(["mitosis cell"])[0]
    assert len(provider.embed("mitosis cell")) == provider.dimensions
    assert provider.version == "deterministic-embedding-v1"


def test_provider_resolution_and_failure():
    provider = DeterministicEmbeddingProvider()
    assert EmbeddingProviderRegistry([provider]).resolve("query") is provider
    with pytest.raises(EmbeddingProviderUnavailable): EmbeddingProviderRegistry([]).resolve()


def test_hybrid_ranking_primitives_are_bounded():
    assert _cosine([1, 0], [1, 0]) == 1
    assert _keyword("cell membrane", "the cell has a membrane") == 1

