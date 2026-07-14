from __future__ import annotations

import hashlib
import math


class EmbeddingProviderUnavailable(RuntimeError):
    code = "provider_unavailable"


class DeterministicEmbeddingProvider:
    """Local, SDK-free reference provider used for deterministic indexing and tests."""
    version = "deterministic-embedding-v1"
    dimensions = 32

    def supports(self, purpose: str) -> bool:
        return purpose in {"retrieval", "indexing", "query"}

    def embed(self, text: str):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Embedding input must contain text.")
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode()).digest()
            vector[int.from_bytes(digest[:2], "big") % self.dimensions] += -1.0 if digest[2] & 1 else 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 8) for value in vector]

    def embed_batch(self, texts):
        return [self.embed(text) for text in texts]


class EmbeddingProviderRegistry:
    def __init__(self, providers):
        self.providers = list(providers)

    def resolve(self, purpose="retrieval"):
        for provider in self.providers:
            if provider.supports(purpose):
                return provider
        raise EmbeddingProviderUnavailable(f"No embedding provider supports {purpose}.")

