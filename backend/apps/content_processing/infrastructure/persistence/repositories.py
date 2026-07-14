from __future__ import annotations

from apps.content_processing.models import (
    ContentProcessingJob,
    ProcessingAttempt,
    ProcessingDiagnostic,
    ProcessingStageResult,
    DocumentHierarchy,
    DocumentHierarchyNode,
    DocumentSegmentation,
    SemanticSegment,
    AcademicImportProposal,
    AcademicPopulationJob,
)


class DjangoContentProcessingJobRepository:
    def get(self, job_id: str) -> ContentProcessingJob:
        return ContentProcessingJob.objects.select_related("resource", "stored_file", "legacy_import_job").get(id=job_id)

    def get_for_update(self, job_id: str) -> ContentProcessingJob:
        return ContentProcessingJob.objects.select_for_update().select_related("resource", "stored_file", "legacy_import_job").get(id=job_id)

    def find_active_by_identity(self, resource_id: str, stored_file_id: str | None, pipeline_version: str) -> ContentProcessingJob | None:
        queryset = ContentProcessingJob.objects.filter(resource_id=resource_id, pipeline_version=pipeline_version).exclude(status="deleted")
        if stored_file_id is None:
            queryset = queryset.filter(stored_file__isnull=True)
        else:
            queryset = queryset.filter(stored_file_id=stored_file_id)
        return queryset.order_by("-created_at").first()

    def save(self, job: ContentProcessingJob) -> ContentProcessingJob:
        job.save()
        return job

    def list_for_resource(self, resource_id: str) -> list[ContentProcessingJob]:
        return list(ContentProcessingJob.objects.filter(resource_id=resource_id).order_by("-created_at"))


class DjangoProcessingAttemptRepository:
    def append(self, attempt: ProcessingAttempt) -> ProcessingAttempt:
        attempt.save()
        return attempt

    def get_active(self, job_id: str) -> ProcessingAttempt | None:
        job = ContentProcessingJob.objects.get(id=job_id)
        return ProcessingAttempt.objects.filter(job=job, attempt_number=job.active_attempt_number).first()

    def get_by_id(self, attempt_id: str) -> ProcessingAttempt:
        return ProcessingAttempt.objects.select_related("job").get(id=attempt_id)

    def list_for_job(self, job_id: str) -> list[ProcessingAttempt]:
        return list(ProcessingAttempt.objects.filter(job_id=job_id).order_by("-attempt_number"))

    def save(self, attempt: ProcessingAttempt) -> ProcessingAttempt:
        attempt.save()
        return attempt


class DjangoProcessingDiagnosticRepository:
    def append(self, diagnostic: ProcessingDiagnostic) -> ProcessingDiagnostic:
        diagnostic.save()
        return diagnostic

    def list_for_job(self, job_id: str) -> list[ProcessingDiagnostic]:
        return list(ProcessingDiagnostic.objects.filter(job_id=job_id).order_by("created_at"))

    def list_for_attempt(self, attempt_id: str) -> list[ProcessingDiagnostic]:
        return list(ProcessingDiagnostic.objects.filter(attempt_id=attempt_id).order_by("created_at"))

    def count_warnings(self, job_id: str) -> int:
        return ProcessingDiagnostic.objects.filter(job_id=job_id, severity__in=["warning", "error", "fatal"]).count()


class DjangoProcessingStageResultRepository:
    def get(self, job_id: str, attempt_id: str, stage: str, result_version: int) -> ProcessingStageResult | None:
        return ProcessingStageResult.objects.filter(job_id=job_id, attempt_id=attempt_id, stage=stage, result_version=result_version).first()

    def exists(self, job_id: str, attempt_id: str, stage: str, result_version: int) -> bool:
        return ProcessingStageResult.objects.filter(job_id=job_id, attempt_id=attempt_id, stage=stage, result_version=result_version).exists()

    def save(self, result: ProcessingStageResult) -> ProcessingStageResult:
        existing = self.get(str(result.job_id), str(result.attempt_id), result.stage, result.result_version)
        if existing is not None:
            return existing
        result.save()
        return result


class DjangoDocumentHierarchyRepository:
    def get_by_id(self, hierarchy_id):
        return DocumentHierarchy.objects.get(id=hierarchy_id)

    def get_for_job_attempt(self, job_id, attempt_id):
        return DocumentHierarchy.objects.filter(job_id=job_id, attempt_id=attempt_id).order_by("-created_at").first()

    def find_existing(self, **identity):
        return DocumentHierarchy.objects.filter(**identity).first()

    def save(self, hierarchy):
        hierarchy.save(); return hierarchy

    def get_root(self, hierarchy_id):
        return DocumentHierarchyNode.objects.get(document_hierarchy_id=hierarchy_id, structural_role="root")

    def get_in_order(self, hierarchy_id):
        return list(DocumentHierarchyNode.objects.filter(document_hierarchy_id=hierarchy_id).order_by("ordinal"))


class DjangoDocumentSegmentationRepository:
    def get_by_id(self, segmentation_id):
        return DocumentSegmentation.objects.get(id=segmentation_id)

    def get_for_job_attempt(self, job_id, attempt_id):
        return DocumentSegmentation.objects.filter(job_id=job_id, attempt_id=attempt_id).order_by("-created_at").first()

    def find_existing(self, **identity):
        return DocumentSegmentation.objects.filter(**identity).first()

    def save(self, segmentation):
        segmentation.save(); return segmentation


class DjangoSemanticSegmentRepository:
    def list_for_segmentation(self, segmentation_id):
        return list(SemanticSegment.objects.filter(document_segmentation_id=segmentation_id).order_by("ordinal"))

    def list_for_node(self, node_id):
        return list(SemanticSegment.objects.filter(hierarchy_node_id=node_id).order_by("ordinal"))

    def get_in_order(self, segmentation_id):
        return self.list_for_segmentation(segmentation_id)


class DjangoAcademicImportProposalRepository:
    def get_by_id(self, proposal_id):
        return AcademicImportProposal.objects.get(id=proposal_id)

    def get_for_job_attempt(self, job_id, attempt_id):
        return AcademicImportProposal.objects.filter(job_id=job_id, attempt_id=attempt_id).order_by("-created_at").first()

    def find_existing(self, **identity):
        return AcademicImportProposal.objects.filter(**identity).first()

    def save(self, proposal):
        proposal.save(); return proposal


class DjangoAcademicPopulationJobRepository:
    def get_for_proposal(self, proposal_id):
        return AcademicPopulationJob.objects.filter(proposal_id=proposal_id).order_by("-created_at").first()

    def find_existing(self, **identity):
        return AcademicPopulationJob.objects.filter(**identity).first()

    def save(self, population_job):
        population_job.save(); return population_job
