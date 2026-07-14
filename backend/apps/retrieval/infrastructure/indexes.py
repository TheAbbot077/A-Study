from __future__ import annotations

import math
from django.db import connection, transaction

from apps.retrieval.domain.policy import RankingPolicy
from apps.retrieval.domain.queries import RetrievalRanking, RetrievalResult
from apps.retrieval.infrastructure.persistence.models import RetrievalChunk, RetrievalReadiness


def _cosine(left, right):
    if not left or not right:
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    norms = math.sqrt(sum(float(a) ** 2 for a in left)) * math.sqrt(sum(float(b) ** 2 for b in right))
    return max(0.0, dot / norms) if norms else 0.0


def _keyword(query, text):
    terms = set(query.lower().split())
    words = set(text.lower().split())
    return len(terms & words) / len(terms) if terms else 0.0


class DjangoHybridRetrievalIndex:
    version = "postgres-hybrid-json-v1"

    def __init__(self, ranking_policy=None):
        self.ranking_policy = ranking_policy or RankingPolicy()

    @transaction.atomic
    def index(self, chunks, embeddings, *, collection=None, population_job=None):
        if len(chunks) != len(embeddings):
            raise ValueError("Every retrieval chunk requires one embedding.")
        keep = []
        for projection, embedding in zip(chunks, embeddings):
            keep.append(projection.identity_key)
            RetrievalChunk.objects.update_or_create(identity_key=projection.identity_key, defaults={
                "collection": collection, "institution_id": projection.institution_id, "subject_id": projection.subject_id, "resource_id": projection.resource_id,
                "section_id": projection.section_id, "concept_id": projection.concept_id, "semantic_segment_id": projection.semantic_segment_id,
                "proposal_id": projection.proposal_id, "population_job": population_job, "proposal_version": projection.proposal_version, "population_version": projection.population_version,
                "chunk_policy_version": projection.chunk_policy_version, "retrieval_version": projection.retrieval_version, "embedding_version": projection.embedding_version,
                "text": projection.text, "chunk_type": projection.chunk_type, "ordering": projection.ordering, "source_page_start": projection.source_page_start,
                "source_page_end": projection.source_page_end, "token_estimate": projection.token_estimate, "confidence": projection.confidence, "checksum": projection.checksum,
                "embedding": list(embedding), "metadata": projection.metadata,
            })
        RetrievalChunk.objects.filter(collection=collection).exclude(identity_key__in=keep).delete()
        return len(keep)

    def update(self, chunk, embedding):
        RetrievalChunk.objects.filter(identity_key=chunk.identity_key).update(embedding=list(embedding), checksum=chunk.checksum)

    def delete(self, chunk_ids):
        count, _ = RetrievalChunk.objects.filter(id__in=chunk_ids).delete(); return count

    def search(self, query, embedding):
        queryset = self._filtered(query.filters).filter(collection__readiness=RetrievalReadiness.INDEXED)
        results = []
        for chunk in queryset:
            vector_score, keyword_score = _cosine(embedding, chunk.embedding), _keyword(query.text, chunk.text)
            final = round(self.ranking_policy.vector_weight * vector_score + self.ranking_policy.keyword_weight * keyword_score, 8)
            metadata = {**chunk.metadata, "proposal_version": chunk.proposal_version, "population_version": chunk.population_version, "chunk_type": chunk.chunk_type}
            results.append(RetrievalResult(str(chunk.id), chunk.text, chunk.token_estimate, metadata, RetrievalRanking(vector_score, keyword_score, final, self.ranking_policy.configuration_version)))
        return sorted(results, key=lambda item: (-item.ranking.final_score, item.chunk_id))[:query.limit]

    def filter(self, filters):
        return [RetrievalResult(str(chunk.id), chunk.text, chunk.token_estimate, chunk.metadata, RetrievalRanking(0, 0, 0, self.ranking_policy.configuration_version)) for chunk in self._filtered(filters)]

    def health(self):
        return {"status": "available", "version": self.version, "indexed_chunks": RetrievalChunk.objects.filter(collection__readiness=RetrievalReadiness.INDEXED).count()}

    def _filtered(self, filters):
        queryset = RetrievalChunk.objects.all()
        for field in ("institution_id", "subject_id", "resource_id", "section_id", "concept_id", "proposal_version", "population_version", "chunk_type"):
            value = getattr(filters, field)
            if value is not None:
                queryset = queryset.filter(**{field: value})
        if filters.source_page_start is not None:
            queryset = queryset.filter(source_page_end__gte=filters.source_page_start)
        if filters.source_page_end is not None:
            queryset = queryset.filter(source_page_start__lte=filters.source_page_end)
        return queryset.order_by("ordering")


class PostgreSQLPgvectorRetrievalIndex(DjangoHybridRetrievalIndex):
    """Optional PostgreSQL+pgvector adapter. SQL stays isolated from the domain.

    Deployments enable this after provisioning the vector extension and a vector
    projection column; the compatibility adapter remains the default.
    """
    version = "postgres-pgvector-hybrid-v1"

    def health(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            available = bool(cursor.fetchone()[0])
        return {"status": "available" if available else "provider_unavailable", "version": self.version, "extension": "vector"}

    def vector_distance_expression(self, parameter="%s"):
        return f"embedding_vector <=> {parameter}::vector"

