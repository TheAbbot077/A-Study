from __future__ import annotations

from dataclasses import dataclass

from apps.academic.domain.models import ContentConcept, ContentSection
from apps.academic_review.domain.models import AcademicPopulationRun


@dataclass(frozen=True)
class AcademicUnit:
    section_id: str
    section_key: str
    section_title: str
    section_order: int
    concept_id: str
    concept_key: str
    concept_title: str
    concept_order: int
    text: str
    semantic_segment_id: str
    source_page_start: int
    source_page_end: int


@dataclass(frozen=True)
class PopulationSnapshot:
    population_run_id: str
    projection_id: str
    processing_job_id: str | None
    resource_id: str
    subject_id: str
    institution_id: str
    source_fingerprint: str
    projection_fingerprint: str
    status: str
    projection_status: str
    expected_sections: int
    expected_concepts: int
    mapped_sections: int
    mapped_concepts: int
    units: tuple[AcademicUnit, ...]


class DjangoApprovedAcademicSynchronizationGateway:
    """Cross-context query adapter. Application code receives immutable values only."""

    def load(self, population_run_id: str) -> PopulationSnapshot | None:
        run = AcademicPopulationRun.objects.select_related(
            "approved_projection__proposal__job", "resource__subject__institution"
        ).prefetch_related(
            "section_mappings__approved_section",
            "concept_mappings__approved_concept__source__semantic_segment",
        ).filter(id=population_run_id).first()
        if run is None:
            return None
        section_mappings = list(run.section_mappings.all())
        concept_mappings = list(run.concept_mappings.all())
        sections = {
            str(item.id): item for item in ContentSection.objects.filter(
                id__in=[mapping.academic_section_id for mapping in section_mappings]
            )
        }
        concepts = {
            str(item.id): item for item in ContentConcept.objects.filter(
                id__in=[mapping.academic_concept_id for mapping in concept_mappings]
            )
        }
        section_keys = {str(item.academic_section_id): item.stable_source_key for item in section_mappings}
        units = []
        for mapping in concept_mappings:
            concept = concepts.get(str(mapping.academic_concept_id))
            section = sections.get(str(mapping.academic_section_id))
            approved = mapping.approved_concept
            segment = approved.source.semantic_segment
            if not concept or not section or not segment:
                continue
            if (
                not section.is_active or section.review_status != "approved"
                or not concept.is_active or concept.review_status != "approved"
                or str(section.learning_resource_id) != str(run.resource_id)
                or str(concept.content_section_id) != str(section.id)
            ):
                continue
            page_start = approved.page_range.get("start") or approved.source.source_page_start or segment.source_page_start
            page_end = approved.page_range.get("end") or approved.source.source_page_end or segment.source_page_end
            units.append(AcademicUnit(
                section_id=str(section.id), section_key=section_keys.get(str(section.id), ""),
                section_title=section.title, section_order=section.sequence_number,
                concept_id=str(concept.id), concept_key=mapping.stable_source_key,
                concept_title=concept.title, concept_order=concept.sequence_number,
                text=concept.description, semantic_segment_id=str(segment.id),
                source_page_start=page_start or 0, source_page_end=page_end or 0,
            ))
        proposal = run.approved_projection.proposal
        processing_job_id = proposal.job_id
        return PopulationSnapshot(
            population_run_id=str(run.id), projection_id=str(run.approved_projection_id),
            processing_job_id=str(processing_job_id) if processing_job_id else None,
            resource_id=str(run.resource_id), subject_id=str(run.subject_id),
            institution_id=str(run.resource.subject.institution_id),
            source_fingerprint=run.projection_fingerprint,
            projection_fingerprint=run.approved_projection.checksum,
            status=run.status, projection_status=run.approved_projection.status,
            expected_sections=run.plan_snapshot.get("expected_section_count", 0),
            expected_concepts=run.plan_snapshot.get("expected_concept_count", 0),
            mapped_sections=len(sections), mapped_concepts=len(concepts),
            units=tuple(sorted(units, key=lambda item: (item.section_order, item.concept_order))),
        )
