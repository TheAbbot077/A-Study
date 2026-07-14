from __future__ import annotations

from apps.academic.domain.models import LearningResource
from apps.content_intelligence.application.text_sanitizer import sanitize_text_value
from apps.content_intelligence.domain.models import (
    ContentExtractionResult as DomainContentExtractionResult,
    ContentImportJob as DomainContentImportJob,
    ContentValidationFinding as DomainContentValidationFinding,
    ParsedConceptCandidate as DomainParsedConceptCandidate,
    ParsedDocument as DomainParsedDocument,
    ParsedSection as DomainParsedSection,
    ParserPipelineRun as DomainParserPipelineRun,
)
from apps.content_intelligence.models import (
    ContentExtractionResult,
    ContentImportJob,
    ContentValidationFinding,
    ParsedConceptCandidate,
    ParsedDocument,
    ParsedSection,
    ParserPipelineRun,
)

ORMContentImportJob = ContentImportJob
ORMParsedDocument = ParsedDocument
ORMParsedSection = ParsedSection
ORMParsedConceptCandidate = ParsedConceptCandidate
ORMContentExtractionResult = ContentExtractionResult
ORMContentValidationFinding = ContentValidationFinding
ORMParserPipelineRun = ParserPipelineRun


def _sanitize_mapping(defaults: dict[str, object]) -> dict[str, object]:
    sanitized: dict[str, object] = {}
    for key, value in defaults.items():
        sanitized_value, _ = sanitize_text_value(value)
        sanitized[key] = sanitized_value
    return sanitized


class DjangoContentImportJobRepository:
    def add(self, job: DomainContentImportJob | ORMContentImportJob) -> DomainContentImportJob | ORMContentImportJob:
        if isinstance(job, DomainContentImportJob):
            return ORMContentImportJob.objects.create(
                learning_resource=job.learning_resource,
                stored_file=job.stored_file,
                format_type=job.format_type,
                requested_by=job.requested_by,
                status=job.status,
                error_message=job.error_message,
                ocr_requested=job.ocr_requested,
                ocr_used=job.ocr_used,
                extraction_confidence=job.extraction_confidence,
                section_confidence=job.section_confidence,
                concept_confidence=job.concept_confidence,
                structural_confidence=job.structural_confidence,
                metadata=job.metadata,
                started_at=job.started_at,
                completed_at=job.completed_at,
            )
        job.save()
        return job

    def save(self, job: DomainContentImportJob | ORMContentImportJob) -> DomainContentImportJob | ORMContentImportJob:
        if isinstance(job, DomainContentImportJob):
            orm_job = self.get(str(job.id))
            orm_job.status = job.status
            orm_job.error_message = job.error_message
            orm_job.ocr_requested = job.ocr_requested
            orm_job.ocr_used = job.ocr_used
            orm_job.extraction_confidence = job.extraction_confidence
            orm_job.section_confidence = job.section_confidence
            orm_job.concept_confidence = job.concept_confidence
            orm_job.structural_confidence = job.structural_confidence
            orm_job.metadata = job.metadata
            orm_job.started_at = job.started_at
            orm_job.completed_at = job.completed_at
            orm_job.save()
            return orm_job
        job.save()
        return job

    def get(self, job_id: str) -> ORMContentImportJob:
        return ORMContentImportJob.objects.get(id=job_id)

    def list_all(self) -> list[ORMContentImportJob]:
        return list(ORMContentImportJob.objects.select_related("learning_resource", "stored_file").order_by("-created_at"))

    def list_for_resource(self, learning_resource: LearningResource) -> list[ORMContentImportJob]:
        return list(ORMContentImportJob.objects.filter(learning_resource=learning_resource).order_by("-created_at"))


class DjangoParsedDocumentRepository:
    def save_document(self, parsed_document: DomainParsedDocument | ORMParsedDocument) -> DomainParsedDocument | ORMParsedDocument:
        if isinstance(parsed_document, DomainParsedDocument):
            orm_document, _ = ORMParsedDocument.objects.update_or_create(
                import_job=parsed_document.import_job,
                defaults=_sanitize_mapping({
                    "title": parsed_document.title,
                    "normalized_text": parsed_document.normalized_text,
                    "format_type": parsed_document.format_type,
                    "extraction_method": parsed_document.extraction_method,
                    "page_count": parsed_document.page_count,
                    "metadata": parsed_document.metadata,
                }),
            )
            return orm_document
        parsed_document.title = sanitize_text_value(parsed_document.title)[0]
        parsed_document.normalized_text = sanitize_text_value(parsed_document.normalized_text)[0]
        parsed_document.extraction_method = sanitize_text_value(parsed_document.extraction_method)[0]
        parsed_document.metadata = sanitize_text_value(parsed_document.metadata)[0]
        parsed_document.save()
        return parsed_document

    def get_for_job(self, job: DomainContentImportJob | ORMContentImportJob) -> ORMParsedDocument | None:
        return ORMParsedDocument.objects.filter(import_job=job).first()

    def replace_sections(
        self,
        parsed_document: DomainParsedDocument | ORMParsedDocument,
        sections: list[DomainParsedSection | ORMParsedSection],
    ) -> list[DomainParsedSection | ORMParsedSection]:
        ORMParsedSection.objects.filter(parsed_document=parsed_document).delete()
        saved_sections: list[DomainParsedSection | ORMParsedSection] = []
        for section in sections:
            if isinstance(section, DomainParsedSection):
                saved_sections.append(
                    ORMParsedSection.objects.create(
                        parsed_document=parsed_document,
                        heading=sanitize_text_value(section.heading)[0],
                        body_text=sanitize_text_value(section.body_text)[0],
                        sequence_number=section.sequence_number,
                        section_type=section.section_type,
                        confidence=section.confidence,
                        metadata=sanitize_text_value(section.metadata)[0],
                    )
                )
                continue
            section.parsed_document = parsed_document
            section.heading = sanitize_text_value(section.heading)[0]
            section.body_text = sanitize_text_value(section.body_text)[0]
            section.metadata = sanitize_text_value(section.metadata)[0]
            section.save()
            saved_sections.append(section)
        return saved_sections

    def replace_concepts(
        self,
        parsed_section: DomainParsedSection | ORMParsedSection,
        concepts: list[DomainParsedConceptCandidate | ORMParsedConceptCandidate],
    ) -> list[DomainParsedConceptCandidate | ORMParsedConceptCandidate]:
        ORMParsedConceptCandidate.objects.filter(parsed_section=parsed_section).delete()
        saved_concepts: list[DomainParsedConceptCandidate | ORMParsedConceptCandidate] = []
        for concept in concepts:
            if isinstance(concept, DomainParsedConceptCandidate):
                saved_concepts.append(
                    ORMParsedConceptCandidate.objects.create(
                        parsed_section=parsed_section,
                        title=sanitize_text_value(concept.title)[0],
                        description=sanitize_text_value(concept.description)[0],
                        learning_objective=sanitize_text_value(concept.learning_objective)[0],
                        sequence_number=concept.sequence_number,
                        confidence=concept.confidence,
                        metadata=sanitize_text_value(concept.metadata)[0],
                    )
                )
                continue
            concept.parsed_section = parsed_section
            concept.title = sanitize_text_value(concept.title)[0]
            concept.description = sanitize_text_value(concept.description)[0]
            concept.learning_objective = sanitize_text_value(concept.learning_objective)[0]
            concept.metadata = sanitize_text_value(concept.metadata)[0]
            concept.save()
            saved_concepts.append(concept)
        return saved_concepts


class DjangoContentExtractionResultRepository:
    def save_result(
        self,
        result: DomainContentExtractionResult | ORMContentExtractionResult,
    ) -> DomainContentExtractionResult | ORMContentExtractionResult:
        if isinstance(result, DomainContentExtractionResult):
            orm_result, _ = ORMContentExtractionResult.objects.update_or_create(
                import_job=result.import_job,
                defaults=_sanitize_mapping({
                    "extracted_text": result.extracted_text,
                    "normalized_text": result.normalized_text,
                    "extraction_method": result.extraction_method,
                    "sufficient_text": result.sufficient_text,
                    "ocr_requested": result.ocr_requested,
                    "ocr_used": result.ocr_used,
                    "char_count": result.char_count,
                    "page_count": result.page_count,
                    "metadata": result.metadata,
                }),
            )
            return orm_result
        result.extracted_text = sanitize_text_value(result.extracted_text)[0]
        result.normalized_text = sanitize_text_value(result.normalized_text)[0]
        result.extraction_method = sanitize_text_value(result.extraction_method)[0]
        result.metadata = sanitize_text_value(result.metadata)[0]
        result.save()
        return result

    def get_for_job(self, job: DomainContentImportJob | ORMContentImportJob) -> ORMContentExtractionResult | None:
        return ORMContentExtractionResult.objects.filter(import_job=job).first()


class DjangoValidationFindingRepository:
    def replace_for_job(
        self,
        job: DomainContentImportJob | ORMContentImportJob,
        findings: list[DomainContentValidationFinding | ORMContentValidationFinding],
    ) -> list[DomainContentValidationFinding | ORMContentValidationFinding]:
        ORMContentValidationFinding.objects.filter(import_job=job).delete()
        saved_findings: list[DomainContentValidationFinding | ORMContentValidationFinding] = []
        for finding in findings:
            if isinstance(finding, DomainContentValidationFinding):
                saved_findings.append(
                    ORMContentValidationFinding.objects.create(
                        import_job=job,
                        severity=finding.severity,
                        finding_type=finding.finding_type,
                        message=finding.message,
                        metadata=finding.metadata,
                    )
                )
                continue
            finding.import_job = job
            finding.message = sanitize_text_value(finding.message)[0]
            finding.metadata = sanitize_text_value(finding.metadata)[0]
            finding.save()
            saved_findings.append(finding)
        return saved_findings

    def list_for_job(self, job: DomainContentImportJob | ORMContentImportJob) -> list[ORMContentValidationFinding]:
        return list(ORMContentValidationFinding.objects.filter(import_job=job).order_by("-created_at"))


class DjangoParserPipelineRunRepository:
    def add(self, run: DomainParserPipelineRun | ORMParserPipelineRun) -> DomainParserPipelineRun | ORMParserPipelineRun:
        if isinstance(run, DomainParserPipelineRun):
            return ORMParserPipelineRun.objects.create(
                import_job=run.import_job,
                status=run.status,
                current_stage=run.current_stage,
                metadata=run.metadata,
                started_at=run.started_at,
                completed_at=run.completed_at,
            )
        run.save()
        return run

    def save(self, run: DomainParserPipelineRun | ORMParserPipelineRun) -> DomainParserPipelineRun | ORMParserPipelineRun:
        if isinstance(run, DomainParserPipelineRun):
            orm_run = ORMParserPipelineRun.objects.get(id=run.id)
            orm_run.status = run.status
            orm_run.current_stage = run.current_stage
            orm_run.metadata = run.metadata
            orm_run.started_at = run.started_at
            orm_run.completed_at = run.completed_at
            orm_run.save()
            return orm_run
        run.save()
        return run

    def list_for_job(self, job: DomainContentImportJob | ORMContentImportJob) -> list[ORMParserPipelineRun]:
        return list(ORMParserPipelineRun.objects.filter(import_job=job).order_by("-created_at"))
