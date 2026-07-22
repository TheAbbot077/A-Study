from __future__ import annotations

from apps.academic.domain.models import ContentConcept, ContentSection, LearningResource
from apps.academic_review.domain.models import AcademicPopulationRun
from apps.content_processing.domain.models import ContentProcessingJob, ProcessingDiagnostic, ProcessingStageResult
from apps.content_processing.domain.extraction import SourceDocumentProfile
from apps.content_processing.domain.teaching_readiness import TeachingReadinessSnapshot
from apps.retrieval.models import RetrievalChunk, RetrievalGeneration, RetrievalSynchronizationRun


class DjangoTeachingReadinessSnapshotGateway:
    """Read-only cross-context adapter returning an immutable policy snapshot."""

    def assemble(self, resource_id: str, policy_version: str) -> TeachingReadinessSnapshot:
        resource = LearningResource.objects.select_related("subject", "stored_file").get(id=resource_id)
        job = ContentProcessingJob.objects.select_related("stored_file").filter(resource_id=resource_id).exclude(status="deleted").order_by("-created_at").first()
        if job is None:
            raise LookupError("READINESS_PROCESSING_JOB_NOT_FOUND")
        attempt = job.attempts.filter(attempt_number=job.active_attempt_number).first()
        proposal = job.academic_import_proposals.order_by("-created_at").first()
        session = proposal.academic_review_sessions.select_related(
            "approved_projection__approval_decision__readiness_snapshot"
        ).order_by("-created_at").first() if proposal else None
        projection = getattr(session, "approved_projection", None) if session else None
        decision = getattr(projection, "approval_decision", None) if projection else None
        population = AcademicPopulationRun.objects.filter(
            approved_projection=projection, status="populated"
        ).order_by("-created_at").first() if projection else None
        synchronization = RetrievalSynchronizationRun.objects.select_related("retrieval_generation").filter(
            academic_population_run=population, status="synchronized"
        ).order_by("-created_at").first() if population else None
        generation = synchronization.retrieval_generation if synchronization else None

        section_ids = list(population.section_mappings.values_list("academic_section_id", flat=True)) if population else []
        concept_ids = list(population.concept_mappings.values_list("academic_concept_id", flat=True)) if population else []
        sections = list(ContentSection.objects.filter(id__in=section_ids))
        concepts = list(ContentConcept.objects.filter(id__in=concept_ids).select_related("content_section"))
        academic_valid = bool(population and sections) and all(
            item.is_active and item.review_status == "approved" and str(item.learning_resource_id) == str(resource.id)
            for item in sections
        ) and all(
            item.is_active and item.review_status == "approved" and item.description.strip()
            and str(item.content_section.learning_resource_id) == str(resource.id)
            for item in concepts
        )

        chunks = list(RetrievalChunk.objects.filter(generation=generation).select_related("section", "concept")) if generation else []
        keys = [chunk.identity_key for chunk in chunks]
        duplicate_count = len(keys) - len(set(keys))
        orphaned_count = sum(
            1 for chunk in chunks
            if str(chunk.resource_id) != str(resource.id)
            or not chunk.section_id
            or (chunk.concept_id and str(chunk.concept.content_section_id) != str(chunk.section_id))
        )
        provenance_valid = bool(chunks) and all(
            chunk.semantic_segment_id and chunk.source_page_start >= 1
            and chunk.source_page_end >= chunk.source_page_start
            and chunk.metadata.get("source_fingerprint")
            for chunk in chunks
        )
        completed_stages = set(ProcessingStageResult.objects.filter(
            job=job, attempt=attempt
        ).values_list("stage", flat=True)) if attempt else set()
        required_outputs = {"extracting", "structuring", "segmenting"}
        blocking_diagnostics = ProcessingDiagnostic.objects.filter(
            job=job, attempt=attempt, severity__in=["error", "fatal"]
        ).count() if attempt else 0
        readiness_snapshot = getattr(decision, "readiness_snapshot", None) if decision else None
        unresolved_review = max(
            0,
            (getattr(readiness_snapshot, "blocking_findings", 0) or 0)
            - (getattr(readiness_snapshot, "resolved_findings", 0) or 0),
        )
        expected_sections = population.plan_snapshot.get("expected_section_count", 0) if population else 0
        expected_concepts = population.plan_snapshot.get("expected_concept_count", 0) if population else 0
        source_fingerprint = (job.stored_file.checksum or "") if job.stored_file_id else ""
        profile = SourceDocumentProfile.objects.filter(job=job, attempt=attempt).order_by("-created_at").first() if attempt else None
        population_fingerprint = population.projection_fingerprint if population else ""
        official_fingerprint = population_fingerprint
        return TeachingReadinessSnapshot(
            resource_id=str(resource.id), subject_id=str(resource.subject_id),
            processing_job_id=str(job.id), processing_attempt_id=str(attempt.id) if attempt else "",
            stored_file_id=str(job.stored_file_id or ""), source_fingerprint=source_fingerprint,
            processing_source_fingerprint=getattr(profile, "source_checksum", ""),
            source_exists=bool(job.stored_file_id), source_available=bool(job.stored_file_id and source_fingerprint),
            processing_status=job.status, processing_attempt_status=getattr(attempt, "status", ""),
            processing_outputs_complete=required_outputs <= completed_stages,
            blocking_diagnostic_count=blocking_diagnostics,
            review_session_id=str(session.id) if session else "", review_status=getattr(session, "status", ""),
            unresolved_review_findings=unresolved_review,
            approval_decision_id=str(decision.id) if decision else "", approval_decision=getattr(decision, "decision", ""),
            approval_actor_authorized=bool(getattr(decision, "decided_by_id", None)),
            approved_projection_id=str(projection.id) if projection else "",
            projection_fingerprint=getattr(projection, "checksum", ""), projection_status=getattr(projection, "status", ""),
            academic_population_run_id=str(population.id) if population else "",
            population_status=getattr(population, "status", ""), population_fingerprint=population_fingerprint,
            expected_section_count=expected_sections, actual_section_count=len(sections),
            expected_concept_count=expected_concepts, actual_concept_count=len(concepts),
            official_academic_fingerprint=official_fingerprint, academic_content_valid=academic_valid,
            retrieval_synchronization_run_id=str(synchronization.id) if synchronization else "",
            synchronization_status=getattr(synchronization, "status", ""),
            synchronization_source_fingerprint=getattr(synchronization, "source_fingerprint", ""),
            manifest_fingerprint=getattr(synchronization, "manifest_fingerprint", ""),
            retrieval_generation_id=str(generation.id) if generation else "",
            generation_status=getattr(generation, "status", ""),
            planned_chunk_count=getattr(synchronization, "planned_chunk_count", 0),
            stored_chunk_count=len(chunks),
            keyword_indexed_count=getattr(synchronization, "keyword_indexed_count", 0),
            vector_indexed_count=getattr(synchronization, "vector_indexed_count", 0),
            failed_chunk_count=getattr(synchronization, "failed_chunk_count", 0),
            duplicate_chunk_count=duplicate_count, orphaned_chunk_count=orphaned_count,
            citation_coverage=getattr(synchronization, "citation_coverage", 0),
            provenance_valid=provenance_valid, policy_version=policy_version,
        )

    def current_lineage_fingerprint(self, resource_id: str, policy_version: str) -> str:
        return self.assemble(resource_id, policy_version).lineage_fingerprint()
