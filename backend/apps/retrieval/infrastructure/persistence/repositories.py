from __future__ import annotations

from dataclasses import asdict
from apps.retrieval.domain.models import CitationTrace
from .models import GroundingCitation, GroundingPackage, RetrievalChunk, RetrievalChunkCollection, RetrievalIndexJob


class RetrievalChunkMapper:
    @staticmethod
    def to_dict(model):
        return {"id": str(model.id), "identity_key": model.identity_key, "text": model.text, "ordering": model.ordering, "checksum": model.checksum, "metadata": dict(model.metadata)}


class DjangoRetrievalChunkRepository:
    def list_by_collection(self, collection_id):
        return [RetrievalChunkMapper.to_dict(item) for item in RetrievalChunk.objects.filter(collection_id=collection_id).order_by("ordering")]

    def get(self, chunk_id):
        return RetrievalChunkMapper.to_dict(RetrievalChunk.objects.get(id=chunk_id))


class DjangoCollectionRepository:
    def get_by_population(self, population_job_id):
        return RetrievalChunkCollection.objects.get(population_job_id=population_job_id)


class DjangoIndexJobRepository:
    def get_or_create(self, population_job_id, retrieval_version, embedding_version):
        return RetrievalIndexJob.objects.get_or_create(population_job_id=population_job_id, retrieval_version=retrieval_version, embedding_version=embedding_version)

    def save(self, job):
        job.save(); return job


class DjangoGroundingPackageRepository:
    def get(self, package_id):
        package = GroundingPackage.objects.prefetch_related("citations").get(id=package_id)
        citations = [CitationTrace(str(c.chunk_id), str(c.institution_id), str(c.subject_id), str(c.resource_id), str(c.section_id), str(c.concept_id) if c.concept_id else None, str(c.semantic_segment_id) if c.semantic_segment_id else None, str(c.proposal_id), str(c.population_job_id), c.source_page_start, c.source_page_end) for c in package.citations.all()]
        return {"id": str(package.id), "query_text": package.query_text, "citations": [asdict(item) for item in citations], "retrieval_statistics": package.retrieval_statistics}


class DjangoGroundingCitationRepository:
    def list_by_package(self, package_id):
        return [{"chunk_id": str(item.chunk_id), "rank": item.rank, "score": item.score, "source_pages": [item.source_page_start, item.source_page_end]} for item in GroundingCitation.objects.filter(package_id=package_id).order_by("rank")]
