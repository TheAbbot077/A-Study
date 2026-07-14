from __future__ import annotations

import logging
from typing import Optional

from apps.academic.services import LearningContentService, LearningResourceService, ResourceIngestionService
from apps.content_intelligence.application.concept_extraction_service import ConceptExtractionService
from apps.content_intelligence.application.confidence_service import ConfidenceScoringService
from apps.content_intelligence.application.document_text_normalization_service import DocumentTextNormalizationService
from apps.content_intelligence.application.extraction_service import ExtractionService
from apps.content_intelligence.application.section_detection_service import SectionDetectionService
from apps.content_intelligence.application.validation_service import ValidationService
from apps.content_intelligence.domain.models import (
    ContentImportJob,
    ParsedConceptCandidate,
    ParsedDocument,
    ParsedSection,
    ParserPipelineRun,
)
from apps.content_intelligence.domain.repositories import (
    ContentImportJobRepository,
    ParsedDocumentRepository,
    ParserPipelineRunRepository,
    ValidationFindingRepository,
)
from apps.content_intelligence.infrastructure.persistence import (
    DjangoContentImportJobRepository,
    DjangoParsedDocumentRepository,
    DjangoParserPipelineRunRepository,
    DjangoValidationFindingRepository,
)
from apps.core.events import BusinessEvent, EventPublisher

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(
        self,
        job_repository: Optional[ContentImportJobRepository] = None,
        parsed_document_repository: Optional[ParsedDocumentRepository] = None,
        validation_repository: Optional[ValidationFindingRepository] = None,
        pipeline_run_repository: Optional[ParserPipelineRunRepository] = None,
        extraction_service: Optional[ExtractionService] = None,
        text_normalization_service: Optional[DocumentTextNormalizationService] = None,
        section_detection_service: Optional[SectionDetectionService] = None,
        concept_extraction_service: Optional[ConceptExtractionService] = None,
        confidence_service: Optional[ConfidenceScoringService] = None,
        validation_service: Optional[ValidationService] = None,
        learning_content_service: Optional[LearningContentService] = None,
        learning_resource_service: Optional[LearningResourceService] = None,
        ingestion_service: Optional[ResourceIngestionService] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.job_repository = job_repository or DjangoContentImportJobRepository()
        self.parsed_document_repository = parsed_document_repository or DjangoParsedDocumentRepository()
        self.validation_repository = validation_repository or DjangoValidationFindingRepository()
        self.pipeline_run_repository = pipeline_run_repository or DjangoParserPipelineRunRepository()
        self.event_publisher = event_publisher or EventPublisher()
        self.extraction_service = extraction_service or ExtractionService(event_publisher=self.event_publisher)
        self.text_normalization_service = text_normalization_service or DocumentTextNormalizationService()
        self.section_detection_service = section_detection_service or SectionDetectionService(event_publisher=self.event_publisher)
        self.concept_extraction_service = concept_extraction_service or ConceptExtractionService(event_publisher=self.event_publisher)
        self.confidence_service = confidence_service or ConfidenceScoringService()
        self.validation_service = validation_service or ValidationService(event_publisher=self.event_publisher)
        self.learning_content_service = learning_content_service or LearningContentService(event_publisher=self.event_publisher)
        self.learning_resource_service = learning_resource_service or LearningResourceService(event_publisher=self.event_publisher)
        self.ingestion_service = ingestion_service or ResourceIngestionService(event_publisher=self.event_publisher)

    def run_pipeline(self, job: ContentImportJob) -> ContentImportJob:
        run = self.pipeline_run_repository.add(ParserPipelineRun(import_job=job, current_stage="starting"))
        try:
            job.start()
            self.job_repository.save(job)
            run.start("extraction")
            self.pipeline_run_repository.save(run)

            extraction_result = self.extraction_service.extract(job)
            normalization_result = self.text_normalization_service.normalize(extraction_result.normalized_text)
            parsed_document = self._save_parsed_document(job, extraction_result, normalization_result)

            run.advance("section_detection")
            self.pipeline_run_repository.save(run)
            sections = self.section_detection_service.detect_sections(parsed_document)
            self.parsed_document_repository.save_document(parsed_document)
            sections = self.parsed_document_repository.replace_sections(parsed_document, sections)

            run.advance("concept_extraction")
            self.pipeline_run_repository.save(run)
            concept_count = 0
            all_concepts: list[ParsedConceptCandidate] = []
            for section in sections:
                concepts = self.concept_extraction_service.extract_concepts(section)
                if hasattr(section, "save"):
                    section.save(update_fields=["metadata", "updated_at"] if hasattr(section, "updated_at") else ["metadata"])
                saved_concepts = self.parsed_document_repository.replace_concepts(section, concepts)
                all_concepts.extend(saved_concepts)
                concept_count += len(saved_concepts)

            job.extraction_confidence = self.confidence_service.score_extraction_quality(extraction_result)
            job.section_confidence = self.confidence_service.score_section_confidence(sections)
            job.concept_confidence = self.confidence_service.score_concept_confidence(all_concepts)
            job.structural_confidence = self.confidence_service.score_structural_consistency(sections)

            run.advance("validation")
            self.pipeline_run_repository.save(run)
            findings = self.validation_service.validate(job, sections, all_concepts, extraction_result.char_count)
            self.validation_repository.replace_for_job(job, findings)

            run.advance("academic_population")
            self.pipeline_run_repository.save(run)
            population_metrics = self._populate_academic_content(job, sections)
            learning_resource = job.learning_resource
            resource_status = getattr(learning_resource, "status", None)
            status_enum = getattr(learning_resource, "Status", None)
            active_status = getattr(status_enum, "ACTIVE", "active")
            if resource_status != active_status and hasattr(learning_resource, "save"):
                self.learning_resource_service.activate_resource(learning_resource)
            self.event_publisher.publish(
                BusinessEvent.create(
                    "content_intelligence.academic_population_completed",
                    payload={
                        "content_import_job_id": str(job.id),
                        "learning_resource_id": str(job.learning_resource_id),
                        "section_count": len(sections),
                        "concept_count": population_metrics["candidates_accepted"],
                    },
                )
            )

            job.complete()
            metadata = dict(job.metadata or {})
            metadata["resource_ready_for_learning"] = bool(sections and population_metrics["candidates_accepted"])
            metadata["finding_count"] = len(findings)
            metadata["semantic_cleanup"] = normalization_result.metadata
            metadata["content_quality"] = {
                "candidates_generated": concept_count,
                "candidates_accepted": population_metrics["candidates_accepted"],
                "candidates_rejected": population_metrics["candidates_rejected"],
                "candidates_manual_review": population_metrics["candidates_manual_review"],
                "duplicate_candidates_removed": population_metrics["duplicate_candidates_removed"],
                "front_matter_sections_skipped": int(
                    self._metadata_dict(getattr(parsed_document, "metadata", None)).get("front_matter_sections_skipped", 0) or 0
                ) + population_metrics["front_matter_sections_skipped"],
                "synthetic_section_titles_skipped": population_metrics["synthetic_section_titles_skipped"],
            }
            metadata.pop("failure", None)
            job.metadata = metadata
            self.job_repository.save(job)
            run.complete()
            self.pipeline_run_repository.save(run)
            self.event_publisher.publish(
                BusinessEvent.create(
                    "content_intelligence.import_completed",
                    payload={
                        "content_import_job_id": str(job.id),
                        "learning_resource_id": str(job.learning_resource_id),
                        "finding_count": len(findings),
                    },
                )
            )
            return job
        except Exception as exc:
            logger.exception("Content intelligence pipeline failed: job_id=%s", job.id)
            metadata = dict(job.metadata or {})
            if hasattr(exc, "details"):
                metadata["failure"] = getattr(exc, "details")
            job.metadata = metadata
            job.fail(str(exc))
            self.job_repository.save(job)
            run.fail(str(exc))
            self.pipeline_run_repository.save(run)
            self.event_publisher.publish(
                BusinessEvent.create(
                    "content_intelligence.import_failed",
                    payload={
                        "content_import_job_id": str(job.id),
                        "learning_resource_id": str(job.learning_resource_id),
                        "error_message": str(exc),
                    },
                )
            )
            raise

    def _save_parsed_document(self, job: ContentImportJob, extraction_result, normalization_result) -> ParsedDocument:
        parsed_document = self.parsed_document_repository.get_for_job(job) or ParsedDocument(import_job=job)
        parsed_document.title = job.learning_resource.title
        parsed_document.normalized_text = normalization_result.cleaned_text
        parsed_document.format_type = job.format_type
        parsed_document.extraction_method = extraction_result.extraction_method
        parsed_document.page_count = extraction_result.page_count
        parsed_document.metadata = {
            "char_count": extraction_result.char_count,
            "normalized_text_char_count": len(normalization_result.normalized_text),
            "cleaned_text_char_count": len(normalization_result.cleaned_text),
            "cleaned_semantic_text": normalization_result.cleaned_text,
            "semantic_cleanup": normalization_result.metadata,
        }
        return self.parsed_document_repository.save_document(parsed_document)

    def _populate_academic_content(self, job: ContentImportJob, sections: list[ParsedSection]) -> dict[str, int]:
        learning_resource = job.learning_resource
        existing_sections = {section.sequence_number: section for section in self.learning_content_service.list_sections(learning_resource)}
        active_section_sequences: set[int] = set()
        metrics = {
            "candidates_accepted": 0,
            "candidates_rejected": 0,
            "candidates_manual_review": 0,
            "duplicate_candidates_removed": 0,
            "front_matter_sections_skipped": 0,
            "synthetic_section_titles_skipped": 0,
        }

        for parsed_section in sections:
            metrics["synthetic_section_titles_skipped"] += int(
                self._metadata_dict(getattr(parsed_section, "metadata", None)).get("synthetic_section_titles_skipped", 0) or 0
            )
            accepted_candidates = []
            for candidate in parsed_section.concept_candidates.all().order_by("sequence_number"):
                candidate_metadata = self._metadata_dict(getattr(candidate, "metadata", None))
                decision = candidate_metadata.get("decision")
                if decision == "accepted":
                    accepted_candidates.append(candidate)
                    metrics["candidates_accepted"] += 1
                elif decision in {"accepted_with_warning", "manual_review"}:
                    metrics["candidates_manual_review"] += 1
                else:
                    metrics["candidates_rejected"] += 1
                if "duplicate_candidate" in (candidate_metadata.get("rejection_reasons") or []):
                    metrics["duplicate_candidates_removed"] += 1

            if not accepted_candidates:
                parsed_section_metadata = self._metadata_dict(getattr(parsed_section, "metadata", None))
                if parsed_section_metadata.get("section_classification") in {"front_matter", "navigation", "reference"}:
                    metrics["front_matter_sections_skipped"] += 1
                continue

            active_section_sequences.add(parsed_section.sequence_number)
            section = existing_sections.get(parsed_section.sequence_number)
            if section is None:
                section = self.learning_content_service.create_section(
                    learning_resource,
                    self._section_title(parsed_section),
                    parsed_section.sequence_number,
                    description=parsed_section.body_text[:1000],
                )
            else:
                section = self.learning_content_service.update_section(
                    section,
                    title=self._section_title(parsed_section),
                    description=parsed_section.body_text[:1000],
                )

            existing_concepts = {concept.sequence_number: concept for concept in self.learning_content_service.list_concepts(section)}
            active_concept_sequences: set[int] = set()
            for next_sequence, candidate in enumerate(accepted_candidates, start=1):
                active_concept_sequences.add(next_sequence)
                concept = existing_concepts.get(candidate.sequence_number)
                concept = existing_concepts.get(next_sequence) if concept is None else concept
                if concept is None:
                    self.learning_content_service.create_concept(
                        section,
                        candidate.title,
                        next_sequence,
                        description=candidate.description,
                        learning_objective=candidate.learning_objective,
                    )
                else:
                    self.learning_content_service.update_concept(
                        concept,
                        title=candidate.title,
                        sequence_number=next_sequence,
                        description=candidate.description,
                        learning_objective=candidate.learning_objective,
                    )
            for existing_sequence, concept in existing_concepts.items():
                if existing_sequence not in active_concept_sequences:
                    self.learning_content_service.delete_concept(concept)

        for sequence_number, section in existing_sections.items():
            if sequence_number not in active_section_sequences:
                self.learning_content_service.delete_section(section)

        return metrics

    def _section_title(self, parsed_section: ParsedSection) -> str:
        semantic_title = self._metadata_dict(getattr(parsed_section, "metadata", None)).get("semantic_title")
        return str(semantic_title or parsed_section.heading)

    def _metadata_dict(self, value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}
