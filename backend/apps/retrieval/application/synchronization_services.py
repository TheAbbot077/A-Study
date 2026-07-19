from __future__ import annotations

import hashlib
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.retrieval.domain.policy import ChunkPolicy
from apps.retrieval.domain.synchronization import (
    CitationSpecification, RetrievalChunkSpecification,
    RetrievalSynchronizationManifest, SynchronizationReadiness,
)
from apps.retrieval.infrastructure.embedding import DeterministicEmbeddingProvider
from apps.retrieval.infrastructure.indexes import DjangoHybridRetrievalIndex
from apps.retrieval.infrastructure.persistence.models import (
    RetrievalChunk, RetrievalGeneration, RetrievalSynchronizationRun,
)
from apps.retrieval.infrastructure.synchronization_gateway import DjangoApprovedAcademicSynchronizationGateway


def _fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


class EvaluateRetrievalSynchronizationReadinessService:
    def __init__(self, gateway=None, embedding_provider=None, index=None):
        self.gateway = gateway or DjangoApprovedAcademicSynchronizationGateway()
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.index = index or DjangoHybridRetrievalIndex()

    def evaluate(self, population_run_id: str) -> SynchronizationReadiness:
        snapshot = self.gateway.load(population_run_id)
        if snapshot is None:
            return SynchronizationReadiness(False, str(population_run_id), None, "", 0, 0, blockers=("POPULATION_RUN_NOT_FOUND",))
        blockers = []
        if snapshot.status != "populated" or snapshot.projection_status != "populated":
            blockers.append("POPULATION_NOT_COMPLETE")
        if snapshot.source_fingerprint != snapshot.projection_fingerprint:
            blockers.append("POPULATION_RESULT_INCONSISTENT")
        if snapshot.mapped_sections != snapshot.expected_sections:
            blockers.append("SECTION_MAPPINGS_INCOMPLETE")
        if snapshot.mapped_concepts != snapshot.expected_concepts or len(snapshot.units) != snapshot.expected_concepts:
            blockers.append("CONCEPT_MAPPINGS_INCOMPLETE")
        if any(not unit.text.strip() for unit in snapshot.units):
            blockers.append("NO_RETRIEVABLE_CONTENT")
        if any(unit.source_page_start < 1 or unit.source_page_end < unit.source_page_start or not unit.semantic_segment_id for unit in snapshot.units):
            blockers.append("CITATION_PROVENANCE_MISSING")
        if not self.embedding_provider.supports("indexing"):
            blockers.append("EMBEDDING_PROVIDER_UNAVAILABLE")
        active = RetrievalGeneration.objects.filter(resource_id=snapshot.resource_id, status=RetrievalGeneration.Status.ACTIVE).first()
        existing = RetrievalSynchronizationRun.objects.filter(
            academic_population_run_id=population_run_id, source_fingerprint=snapshot.source_fingerprint,
            status=RetrievalSynchronizationRun.Status.SYNCHRONIZED,
        ).first()
        return SynchronizationReadiness(
            not blockers, str(population_run_id), snapshot.resource_id, snapshot.source_fingerprint,
            snapshot.expected_sections, snapshot.expected_concepts,
            str(existing.id) if existing else None, str(active.id) if active else None,
            tuple(dict.fromkeys(blockers)),
        )


class BuildRetrievalSynchronizationManifestService:
    CHUNK_POLICY_VERSION = ChunkPolicy().configuration_version
    CITATION_POLICY_VERSION = "academic-citation-v1"
    RETRIEVAL_SCHEMA_VERSION = "approved-academic-retrieval-v1"

    def __init__(self, gateway=None, embedding_provider=None, index=None):
        self.gateway = gateway or DjangoApprovedAcademicSynchronizationGateway()
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.index = index or DjangoHybridRetrievalIndex()

    def build(self, population_run_id: str) -> RetrievalSynchronizationManifest:
        snapshot = self.gateway.load(population_run_id)
        if snapshot is None:
            raise ValidationError("POPULATION_RUN_NOT_FOUND")
        chunks = []
        for ordinal, unit in enumerate(snapshot.units, 1):
            text = " ".join((unit.text or "").replace("\x00", " ").split())
            if not text:
                raise ValidationError("NO_RETRIEVABLE_CONTENT")
            content_fingerprint = _fingerprint([unit.concept_id, text])
            stable_key = _fingerprint([
                snapshot.resource_id, unit.section_key, unit.concept_key, content_fingerprint,
                ordinal, self.CHUNK_POLICY_VERSION, self.RETRIEVAL_SCHEMA_VERSION,
            ])
            citation = CitationSpecification(
                unit.source_page_start, unit.source_page_end, unit.semantic_segment_id,
                snapshot.source_fingerprint, f"{unit.section_title}, pp. {unit.source_page_start}-{unit.source_page_end}",
            )
            chunks.append(RetrievalChunkSpecification(
                stable_key, snapshot.resource_id, unit.section_id, unit.concept_id, text, ordinal,
                content_fingerprint, citation,
                {"section_title": unit.section_title, "concept_title": unit.concept_title,
                 "population_run_id": snapshot.population_run_id, "approved_projection_id": snapshot.projection_id},
            ))
        if not chunks:
            raise ValidationError("NO_RETRIEVABLE_CONTENT")
        material = {
            "population": snapshot.population_run_id, "projection": snapshot.projection_id,
            "resource": snapshot.resource_id, "subject": snapshot.subject_id,
            "source": snapshot.source_fingerprint, "chunks": [chunk.stable_key for chunk in chunks],
            "chunk_policy": self.CHUNK_POLICY_VERSION, "citation_policy": self.CITATION_POLICY_VERSION,
            "schema": self.RETRIEVAL_SCHEMA_VERSION, "embedding": self.embedding_provider.version,
            "index": self.index.version,
        }
        return RetrievalSynchronizationManifest(
            snapshot.population_run_id, snapshot.projection_id, snapshot.resource_id, snapshot.subject_id,
            snapshot.source_fingerprint, _fingerprint(material), self.CHUNK_POLICY_VERSION,
            self.CITATION_POLICY_VERSION, self.RETRIEVAL_SCHEMA_VERSION,
            self.embedding_provider.version, self.index.version, tuple(chunks),
        )


class SynchronizeApprovedAcademicRetrievalService:
    def __init__(self, readiness=None, builder=None, gateway=None, embedding_provider=None, events=None):
        self.gateway = gateway or DjangoApprovedAcademicSynchronizationGateway()
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.readiness = readiness or EvaluateRetrievalSynchronizationReadinessService(self.gateway, self.embedding_provider)
        self.builder = builder or BuildRetrievalSynchronizationManifestService(self.gateway, self.embedding_provider)
        self.events = events or EventPublisher()

    def execute(self, *, population_run_id, expected_source_fingerprint, idempotency_key, actor=None, trigger="staff", reason=""):
        key = (idempotency_key or "").strip()
        if not key:
            raise ValidationError("Blank idempotency key.", code="SYNCHRONIZATION_CONFLICT")
        if trigger == "staff" and (actor is None or not actor.is_staff):
            raise PermissionDenied("SYNCHRONIZATION_NOT_AUTHORIZED")
        request_fingerprint = _fingerprint([str(population_run_id), expected_source_fingerprint, trigger])
        replay = RetrievalSynchronizationRun.objects.filter(idempotency_key=key).first()
        if replay:
            if replay.request_fingerprint != request_fingerprint:
                raise ValidationError("SYNCHRONIZATION_CONFLICT")
            return replay, True
        readiness = self.readiness.evaluate(str(population_run_id))
        if not readiness.ready:
            raise ValidationError(list(readiness.blockers))
        if readiness.source_fingerprint != expected_source_fingerprint:
            raise ValidationError("SOURCE_VERSION_CONFLICT")
        manifest = self.builder.build(str(population_run_id))
        equivalent = RetrievalSynchronizationRun.objects.filter(
            manifest_fingerprint=manifest.manifest_fingerprint,
            status__in=[RetrievalSynchronizationRun.Status.SYNCHRONIZING, RetrievalSynchronizationRun.Status.SYNCHRONIZED],
        ).first()
        if equivalent:
            return equivalent, True
        snapshot = self.gateway.load(str(population_run_id))
        with transaction.atomic():
            run = RetrievalSynchronizationRun.objects.create(
                academic_population_run_id=population_run_id, approved_projection_id=manifest.approved_projection_id,
                processing_job_id=snapshot.processing_job_id, resource_id=manifest.resource_id, subject_id=manifest.subject_id,
                requested_by=actor, trigger=trigger, reason=reason, idempotency_key=key,
                request_fingerprint=request_fingerprint, source_fingerprint=manifest.source_fingerprint,
                manifest_fingerprint=manifest.manifest_fingerprint, planned_chunk_count=len(manifest.chunks),
            )
            generation = RetrievalGeneration.objects.create(
                resource_id=manifest.resource_id, subject_id=manifest.subject_id,
                source_fingerprint=manifest.source_fingerprint, manifest_fingerprint=manifest.manifest_fingerprint,
                chunk_count=len(manifest.chunks),
            )
            run.retrieval_generation = generation
            run.start()
            run.save()
            transaction.on_commit(lambda: self._publish_started(run, generation))
        try:
            embeddings = self.embedding_provider.embed_batch([chunk.text for chunk in manifest.chunks])
            if len(embeddings) != len(manifest.chunks):
                raise ValidationError("EMBEDDING_FAILED")
            rows = []
            for spec, embedding in zip(manifest.chunks, embeddings):
                rows.append(RetrievalChunk(
                    generation=generation, identity_key=spec.stable_key, institution_id=snapshot.institution_id,
                    subject_id=manifest.subject_id, resource_id=manifest.resource_id, section_id=spec.section_id,
                    concept_id=spec.concept_id, semantic_segment_id=spec.citation.semantic_segment_id,
                    proposal_version="", population_version=str(population_run_id),
                    chunk_policy_version=manifest.chunk_policy_version, retrieval_version=manifest.retrieval_schema_version,
                    embedding_version=manifest.embedding_version, text=spec.text, chunk_type="academic_concept",
                    ordering=spec.ordinal, source_page_start=spec.citation.source_page_start,
                    source_page_end=spec.citation.source_page_end, token_estimate=max(1, len(spec.text.split())),
                    confidence=1, checksum=spec.content_fingerprint, embedding=list(embedding),
                    metadata={**spec.metadata, "citation_label": spec.citation.label,
                              "source_fingerprint": spec.citation.source_fingerprint},
                ))
            RetrievalChunk.objects.bulk_create(rows)
            with transaction.atomic():
                locked = RetrievalSynchronizationRun.objects.select_for_update().get(id=run.id)
                current = self.gateway.load(str(population_run_id))
                if current.source_fingerprint != manifest.source_fingerprint:
                    raise ValidationError("SOURCE_VERSION_CONFLICT")
                generation.status = RetrievalGeneration.Status.VALIDATING
                generation.save(update_fields=["status"])
                actual = RetrievalChunk.objects.filter(generation=generation).count()
                locked.indexed_chunk_count = locked.keyword_indexed_count = locked.vector_indexed_count = actual
                locked.citation_coverage = 1 if actual == len(manifest.chunks) else 0
                prior = RetrievalGeneration.objects.select_for_update().filter(
                    resource_id=manifest.resource_id, status=RetrievalGeneration.Status.ACTIVE
                ).exclude(id=generation.id).first()
                generation.status, generation.promoted_at = RetrievalGeneration.Status.ACTIVE, timezone.now()
                generation.save(update_fields=["status", "promoted_at"])
                if prior:
                    prior.status, prior.superseded_at = RetrievalGeneration.Status.SUPERSEDED, timezone.now()
                    prior.save(update_fields=["status", "superseded_at"])
                locked.complete()
                locked.save()
                transaction.on_commit(lambda: self._publish_completion(locked, prior))
            return locked, False
        except Exception as exc:
            with transaction.atomic():
                failed = RetrievalSynchronizationRun.objects.select_for_update().get(id=run.id)
                failed.fail(getattr(exc, "code", None) or "SYNCHRONIZATION_FAILED", str(exc)[:500])
                failed.save()
                generation.status = RetrievalGeneration.Status.FAILED
                generation.save(update_fields=["status"])
                transaction.on_commit(lambda: self.events.publish(BusinessEvent.create(
                    "retrieval_synchronization.failed", payload={"synchronization_run_id": str(failed.id), "failure_code": failed.failure_code}
                )))
            raise

    def _publish_completion(self, run, prior):
        self.events.publish(BusinessEvent.create("retrieval_generation.promoted", payload={
            "generation_id": str(run.retrieval_generation_id), "resource_id": str(run.resource_id),
        }))
        if prior:
            self.events.publish(BusinessEvent.create("retrieval_generation.superseded", payload={
                "generation_id": str(prior.id), "replacement_generation_id": str(run.retrieval_generation_id),
            }))
        self.events.publish(BusinessEvent.create("retrieval_synchronization.completed", payload={
            "synchronization_run_id": str(run.id), "academic_population_run_id": str(run.academic_population_run_id),
            "approved_projection_id": str(run.approved_projection_id), "resource_id": str(run.resource_id),
            "subject_id": str(run.subject_id), "source_fingerprint": run.source_fingerprint,
            "manifest_fingerprint": run.manifest_fingerprint, "retrieval_generation_id": str(run.retrieval_generation_id),
            "planned_chunk_count": run.planned_chunk_count, "indexed_chunk_count": run.indexed_chunk_count,
            "keyword_indexed_count": run.keyword_indexed_count,
            "vector_indexed_count": run.vector_indexed_count, "citation_coverage": run.citation_coverage,
        }))

    def _publish_started(self, run, generation):
        payload = {
            "synchronization_run_id": str(run.id),
            "academic_population_run_id": str(run.academic_population_run_id),
            "generation_id": str(generation.id), "resource_id": str(run.resource_id),
        }
        self.events.publish(BusinessEvent.create("retrieval_synchronization.planned", payload=payload))
        self.events.publish(BusinessEvent.create("retrieval_synchronization.started", payload=payload))
