from __future__ import annotations

from apps.content_processing.application.document_services import ExtractDocumentService, InspectSourceDocumentService
from apps.content_processing.application.structure_services import BuildSemanticSegmentsService, ReconstructDocumentHierarchyService
from apps.content_processing.application.proposal_services import AutomaticProposalAcceptanceService, ApproveProposalService, GenerateAcademicImportProposalService, PopulateAcademicPlatformService
from apps.content_processing.application.services import DiagnosticRecord, ProcessingStageExecutionResult
from apps.content_processing.domain.models import ContentProcessingJob, DiagnosticSeverity, JobStatus, ProcessingStage
from apps.content_processing.models import SourceDocumentProfile


def _diagnostics(stage, warnings):
    return tuple(DiagnosticRecord(stage=stage, severity=DiagnosticSeverity.WARNING, code=item.get("code", "extraction_warning"), public_message=item.get("message", "Document processing completed with a warning."), details={key: value for key, value in item.items() if key not in {"code", "message"}}, source_component="layout_extraction") for item in warnings)


class InspectSourceDocumentProcessor:
    def __init__(self, service=None) -> None:
        self.service = service or InspectSourceDocumentService()

    def supports(self, stage):
        return stage == ProcessingStage.INSPECTING

    def execute(self, context):
        profile, warnings = self.service.execute(context)
        return ProcessingStageExecutionResult(ProcessingStage.INSPECTING, ProcessingStage.EXTRACTING, ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.INSPECTING], _diagnostics(ProcessingStage.INSPECTING, warnings), {"source_document_profile_id": str(profile.id)}, profile.source_checksum)


class ExtractSourceDocumentProcessor:
    def __init__(self, service=None) -> None:
        self.service = service or ExtractDocumentService()

    def supports(self, stage):
        return stage == ProcessingStage.EXTRACTING

    def execute(self, context):
        profile = SourceDocumentProfile.objects.get(job_id=context.job_id, attempt_id=context.attempt_id)
        extraction, warnings = self.service.execute(context, profile)
        return ProcessingStageExecutionResult(ProcessingStage.EXTRACTING, ProcessingStage.STRUCTURING, ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.EXTRACTING], _diagnostics(ProcessingStage.EXTRACTING, warnings), {"source_document_profile_id": str(profile.id), "document_extraction_id": str(extraction.id)}, extraction.result_checksum)


class ReconstructDocumentHierarchyProcessor:
    def __init__(self, service=None) -> None:
        self.service = service or ReconstructDocumentHierarchyService()

    def supports(self, stage):
        return stage == ProcessingStage.STRUCTURING

    def execute(self, context):
        hierarchy, nodes, warnings = self.service.execute(context)
        return ProcessingStageExecutionResult(ProcessingStage.STRUCTURING, ProcessingStage.SEGMENTING, ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.STRUCTURING], _diagnostics(ProcessingStage.STRUCTURING, warnings), {"document_hierarchy_id": str(hierarchy.id), "root_node_id": str(hierarchy.root_node_id), "node_count": len(nodes)}, hierarchy.result_checksum)


class BuildSemanticSegmentsProcessor:
    def __init__(self, service=None) -> None:
        self.service = service or BuildSemanticSegmentsService()

    def supports(self, stage):
        return stage == ProcessingStage.SEGMENTING

    def execute(self, context):
        segmentation, segments, warnings = self.service.execute(context)
        return ProcessingStageExecutionResult(ProcessingStage.SEGMENTING, ProcessingStage.VALIDATING, ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.SEGMENTING], _diagnostics(ProcessingStage.SEGMENTING, warnings), {"document_segmentation_id": str(segmentation.id), "segment_count": len(segments)}, segmentation.result_checksum)


class GenerateAcademicImportProposalProcessor:
    def __init__(self, service=None, approval_service=None, acceptance_service=None) -> None:
        self.service = service or GenerateAcademicImportProposalService()
        self.approval_service = approval_service or ApproveProposalService()
        self.acceptance_service = acceptance_service or AutomaticProposalAcceptanceService()

    def supports(self, stage):
        return stage == ProcessingStage.VALIDATING

    def execute(self, context):
        proposal, warnings = self.service.execute(context)
        acceptance = self.acceptance_service.evaluate(proposal)
        if proposal.review_state == "ready_for_review" and acceptance.eligible:
            self.approval_service.approve(
                proposal,
                reason="Approved by the explicit deterministic automatic-acceptance policy.",
                automatic_acceptance=True,
                policy_version=acceptance.policy_version,
                eligibility_reasons=acceptance.reasons,
            )
        next_stage = ProcessingStage.POPULATING if acceptance.eligible else None
        return ProcessingStageExecutionResult(ProcessingStage.VALIDATING, next_stage, ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.VALIDATING], _diagnostics(ProcessingStage.VALIDATING, warnings), {"academic_import_proposal_id": str(proposal.id), "review_state": proposal.review_state, "population_state": proposal.population_state, "section_count": proposal.statistics.get("section_count", 0), "concept_count": proposal.statistics.get("concept_count", 0)}, proposal.result_checksum)


class PopulateAcademicPlatformProcessor:
    def __init__(self, service=None) -> None:
        self.service = service or PopulateAcademicPlatformService()

    def supports(self, stage):
        return stage == ProcessingStage.POPULATING

    def execute(self, context):
        population, warnings = self.service.execute(context)
        return ProcessingStageExecutionResult(ProcessingStage.POPULATING, ProcessingStage.INDEXING, ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.POPULATING], _diagnostics(ProcessingStage.POPULATING, warnings), {"academic_population_job_id": str(population.id), "proposal_id": str(population.proposal_id), "created_sections": population.created_sections, "updated_sections": population.updated_sections, "created_concepts": population.created_concepts, "updated_concepts": population.updated_concepts}, population.checksum)


class IndexAcademicPopulationProcessor:
    def __init__(self, service=None) -> None:
        from apps.retrieval.application import IndexAcademicPopulationService
        self.service = service or IndexAcademicPopulationService()

    def supports(self, stage):
        return stage == ProcessingStage.INDEXING

    def execute(self, context):
        from apps.content_processing.models import AcademicPopulationJob
        population = AcademicPopulationJob.objects.select_related("proposal").get(job_id=context.job_id, attempt_id=context.attempt_id, status="populated")
        index_job = self.service.execute(population)
        if index_job.status != "indexed":
            error = RuntimeError("The retrieval index did not reach indexed readiness.")
            error.code = index_job.failure_code or "index_failed"
            raise error
        return ProcessingStageExecutionResult(
            ProcessingStage.INDEXING, None, ContentProcessingJob.STAGE_PROGRESS[ProcessingStage.INDEXING], (),
            {"retrieval_index_job_id": str(index_job.id), "retrieval_collection_id": str(index_job.collection_id), "indexed_count": index_job.indexed_count, "retrieval_readiness": index_job.status},
            index_job.checksum, terminal_status=JobStatus.READY_FOR_TEACHING,
        )
