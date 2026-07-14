from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from django.db import transaction

from apps.core.events import BusinessEvent, EventPublisher
from apps.retrieval.domain.models import ChunkProjection
from apps.retrieval.domain.policy import ChunkPolicy, RankingPolicy
from apps.retrieval.domain.queries import RetrievalQuery
from apps.retrieval.infrastructure.embedding import DeterministicEmbeddingProvider
from apps.retrieval.infrastructure.indexes import DjangoHybridRetrievalIndex
from apps.retrieval.infrastructure.persistence.models import GroundingCitation, GroundingPackage, RetrievalChunk, RetrievalChunkCollection, RetrievalDiagnostic, RetrievalIndexJob, RetrievalReadiness, RetrievalStatistic


def _checksum(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def _normalize(text: str) -> str:
    return " ".join((text or "").replace("\x00", " ").split())


class RetrievalChunkBuilder:
    RETRIEVAL_VERSION = "retrieval-v1"

    def __init__(self, policy=None, embedding_version="deterministic-embedding-v1"):
        self.policy = policy or ChunkPolicy()
        self.embedding_version = embedding_version

    def build(self, population_job):
        proposal = population_job.proposal
        if population_job.status != "populated" or proposal.review_state not in {"approved", "approved_with_edits"}:
            raise ValueError("Only an approved, completed Academic Population can be projected into retrieval.")
        candidates = []
        proposed = proposal.proposed_concepts.select_related(
            "proposed_section__populated_section__learning_resource__subject__institution", "populated_concept", "semantic_segment"
        ).order_by("proposed_section__ordering", "ordering")
        ordering = 0
        for item in proposed:
            section, concept, segment = item.proposed_section.populated_section, item.populated_concept, item.semantic_segment
            if section is None or section.review_status != "approved" or concept is None or concept.review_status != "approved" or segment is None:
                continue
            page_start = item.source_page_start or segment.source_page_start
            page_end = item.source_page_end or segment.source_page_end
            if not page_start or not page_end or page_end < page_start:
                raise ValueError("Approved retrieval evidence requires valid source pages.")
            text = _normalize(segment.normalized_text or item.supporting_text or concept.description)
            for part in self._semantic_parts(text):
                ordering += 1
                resource = section.learning_resource
                identity_payload = [population_job.id, proposal.proposal_version, self.policy.configuration_version, self.RETRIEVAL_VERSION, self.embedding_version, segment.id, ordering, part]
                checksum = _checksum(identity_payload)
                candidates.append(ChunkProjection(
                    identity_key=checksum, text=part, ordering=ordering, token_estimate=self.policy.estimate_tokens(part), confidence=min(1, max(0, min(item.confidence, segment.confidence))),
                    chunk_type=segment.segment_type, source_page_start=page_start, source_page_end=page_end,
                    institution_id=str(resource.subject.institution_id), subject_id=str(resource.subject_id), resource_id=str(resource.id), section_id=str(section.id), concept_id=str(concept.id), semantic_segment_id=str(segment.id),
                    proposal_id=str(proposal.id), proposal_version=proposal.proposal_version, population_version=population_job.population_version,
                    chunk_policy_version=self.policy.configuration_version, retrieval_version=self.RETRIEVAL_VERSION, embedding_version=self.embedding_version, checksum=checksum,
                    metadata={"section_title": section.title, "concept_title": concept.title, "population_job_id": str(population_job.id)},
                ))
        if not candidates:
            raise ValueError("The Academic Population produced no approved retrievable content.")
        collection_checksum = _checksum([item.checksum for item in candidates])
        collection, _ = RetrievalChunkCollection.objects.update_or_create(
            population_job=population_job, population_version=population_job.population_version, chunk_policy_version=self.policy.configuration_version, retrieval_version=self.RETRIEVAL_VERSION, embedding_version=self.embedding_version,
            defaults={"resource": proposal.resource, "proposal": proposal, "population_version": population_job.population_version, "chunk_policy_version": self.policy.configuration_version, "retrieval_version": self.RETRIEVAL_VERSION, "embedding_version": self.embedding_version, "chunk_count": len(candidates), "checksum": collection_checksum},
        )
        return collection, candidates

    def _semantic_parts(self, text):
        if not text:
            return []
        if self.policy.estimate_tokens(text) <= self.policy.maximum_chunk_size:
            return [text]
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]
        parts, current = [], []
        for sentence in sentences:
            if self.policy.estimate_tokens(sentence) > self.policy.maximum_chunk_size:
                words, window = sentence.split(), []
                for word in words:
                    candidate = _normalize(" ".join(window + [word]))
                    if window and self.policy.estimate_tokens(candidate) > self.policy.maximum_chunk_size:
                        if current:
                            parts.append(_normalize(" ".join(current))); current = []
                        parts.append(_normalize(" ".join(window)))
                        window = [word]
                    else:
                        window.append(word)
                sentence = _normalize(" ".join(window))
            proposed = _normalize(" ".join(current + [sentence]))
            if current and self.policy.estimate_tokens(proposed) > self.policy.maximum_chunk_size:
                parts.append(_normalize(" ".join(current)))
                current = [sentence]
            else:
                current.append(sentence)
        if current:
            parts.append(_normalize(" ".join(current)))
        return parts


class IndexAcademicPopulationService:
    def __init__(self, builder=None, embedding_provider=None, index=None, event_publisher=None):
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.builder = builder or RetrievalChunkBuilder(embedding_version=self.embedding_provider.version)
        self.index = index or DjangoHybridRetrievalIndex()
        self.events = event_publisher or EventPublisher()

    @transaction.atomic
    def execute(self, population_job):
        index_job, _ = RetrievalIndexJob.objects.get_or_create(population_job=population_job, retrieval_version=self.builder.RETRIEVAL_VERSION, embedding_version=self.embedding_provider.version)
        if index_job.status == RetrievalReadiness.INDEXED:
            return index_job
        index_job.start(); index_job.save()
        self.events.publish(BusinessEvent.create("retrieval.index_started", payload={"index_job_id": str(index_job.id), "population_job_id": str(population_job.id)}))
        try:
            collection, chunks = self.builder.build(population_job)
            collection.readiness = RetrievalReadiness.INDEXING; collection.save(update_fields=["readiness"])
            index_job.collection, index_job.chunk_count = collection, len(chunks); index_job.save(update_fields=["collection", "chunk_count"])
            self.events.publish(BusinessEvent.create("retrieval.chunk_collection_created", payload={"collection_id": str(collection.id), "chunk_count": len(chunks)}))
            embeddings = self.embedding_provider.embed_batch([chunk.text for chunk in chunks])
            self.events.publish(BusinessEvent.create("retrieval.embedding_completed", payload={"index_job_id": str(index_job.id), "embedding_version": self.embedding_provider.version, "chunk_count": len(chunks)}))
            indexed = self.index.index(chunks, embeddings, collection=collection, population_job=population_job)
            checksum = _checksum([collection.checksum, indexed, self.index.version])
            index_job.statistics = {"chunk_count": len(chunks), "indexed_count": indexed, "index_version": self.index.version}
            index_job.complete(indexed, checksum); index_job.save()
            RetrievalStatistic.objects.update_or_create(index_job=index_job, defaults={"collection": collection, "chunk_count": len(chunks), "indexed_count": indexed, "embedding_batch_count": 1, "ranking_policy_version": "hybrid-ranking-v1", "values": index_job.statistics})
            collection.readiness, collection.completed_at = RetrievalReadiness.INDEXED, index_job.completed_at; collection.save(update_fields=["readiness", "completed_at"])
            self.events.publish(BusinessEvent.create("retrieval.index_completed", payload={"index_job_id": str(index_job.id), "indexed_count": indexed}))
            self.events.publish(BusinessEvent.create("retrieval.readiness_changed", payload={"collection_id": str(collection.id), "readiness": RetrievalReadiness.INDEXED}))
            return index_job
        except Exception:
            index_job.fail("index_failed"); index_job.save()
            RetrievalDiagnostic.objects.create(index_job=index_job, severity="error", code=index_job.failure_code, message="Retrieval indexing failed.")
            if index_job.collection_id:
                index_job.collection.readiness = RetrievalReadiness.FAILED; index_job.collection.save(update_fields=["readiness"])
            self.events.publish(BusinessEvent.create("retrieval.index_failed", payload={"index_job_id": str(index_job.id), "failure_code": index_job.failure_code}))
            return index_job


class BuildGroundingPackageService:
    def __init__(self, embedding_provider=None, index=None, ranking_policy=None, event_publisher=None):
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.index = index or DjangoHybridRetrievalIndex(ranking_policy=ranking_policy or RankingPolicy())
        self.events = event_publisher or EventPublisher()

    @transaction.atomic
    def execute(self, query: RetrievalQuery):
        results = self.index.search(query, self.embedding_provider.embed(query.text))
        selected, used = [], 0
        for result in results:
            if used + result.token_estimate > query.token_budget:
                continue
            selected.append(result); used += result.token_estimate
        checksum = _checksum([query.text, asdict(query.filters), [(r.chunk_id, r.ranking.final_score) for r in selected], query.token_budget])
        chunks = {str(item.id): item for item in RetrievalChunk.objects.filter(id__in=[r.chunk_id for r in selected])}
        package, _ = GroundingPackage.objects.get_or_create(checksum=checksum, defaults={
            "query_text": query.text, "retrieved_chunk_ids": [r.chunk_id for r in selected], "confidence_scores": [r.ranking.final_score for r in selected],
            "ranking_metadata": {"policy": self.index.ranking_policy.configuration_version}, "retrieval_rationale": "Hybrid vector, keyword, and Academic metadata ranking.",
            "metadata_filters": asdict(query.filters), "proposal_versions": sorted({str(r.metadata.get("proposal_version")) for r in selected}), "population_versions": sorted({str(r.metadata.get("population_version")) for r in selected}),
            "token_budget_summary": {"budget": query.token_budget, "used": used, "remaining": query.token_budget-used}, "retrieval_statistics": {"returned_count": len(selected), "tokens_used": used},
        })
        if not package.citations.exists():
            GroundingCitation.objects.bulk_create([GroundingCitation(package=package, chunk=chunks[r.chunk_id], institution_id=chunks[r.chunk_id].institution_id, subject_id=chunks[r.chunk_id].subject_id, resource_id=chunks[r.chunk_id].resource_id, section_id=chunks[r.chunk_id].section_id, concept_id=chunks[r.chunk_id].concept_id, semantic_segment_id=chunks[r.chunk_id].semantic_segment_id, proposal_id=chunks[r.chunk_id].proposal_id, population_job_id=chunks[r.chunk_id].population_job_id, source_page_start=chunks[r.chunk_id].source_page_start, source_page_end=chunks[r.chunk_id].source_page_end, rank=i, score=r.ranking.final_score) for i, r in enumerate(selected, 1)])
        self.events.publish(BusinessEvent.create("grounding.package_created", payload={"grounding_package_id": str(package.id), "citation_count": len(selected)}))
        return package
