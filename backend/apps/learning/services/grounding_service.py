from __future__ import annotations

from typing import Optional

from apps.core.events import BusinessEvent, EventPublisher
from apps.learning.domain.models import (
    ContextConceptSnapshot,
    ContextCurriculumSnapshot,
    ContextResourceSnapshot,
    ContextSectionSnapshot,
    GroundedTeachingPackage,
    PedagogicalContext,
    PrimaryEvidence,
    SourceReference,
    SupportingEvidence,
)


class GroundingService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def build_grounding_package(self, context: PedagogicalContext) -> GroundedTeachingPackage:
        primary_concept = context.concept
        primary_evidence = self._build_primary_evidence(primary_concept)
        supporting_evidence = self._build_supporting_evidence(primary_concept)
        source_references = [primary_evidence.source_reference]
        source_references.extend(evidence.source_reference for evidence in supporting_evidence)

        package = GroundedTeachingPackage(
            pedagogical_context=context,
            primary_concept=primary_concept,
            primary_instructional_evidence=primary_evidence,
            supporting_evidence=supporting_evidence,
            source_references=source_references,
            review_status=primary_concept.review_status,
            quality_status=primary_concept.quality_status,
            grounding_confidence=self._calculate_grounding_confidence(primary_evidence, supporting_evidence),
            metadata={"source": "grounding_service"},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.grounding_package_created",
                payload={
                    "session_id": context.session_id,
                    "learner_id": context.learner.learner_id,
                    "content_concept_id": primary_concept.content_concept_id,
                    "source_reference_count": len(source_references),
                },
            )
        )
        return package

    def validate_grounding(self, package: GroundedTeachingPackage) -> list[str]:
        validation_errors: list[str] = []

        if package.primary_concept is None:
            validation_errors.append("Grounded teaching package must contain a primary concept.")
        if package.primary_instructional_evidence is None:
            validation_errors.append("Grounded teaching package must contain primary evidence.")
        if not package.source_references:
            validation_errors.append("Grounded teaching package must preserve source references.")

        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.grounding_validated",
                payload={
                    "session_id": package.pedagogical_context.session_id,
                    "learner_id": package.pedagogical_context.learner.learner_id,
                    "content_concept_id": self._content_concept_id(package),
                    "is_valid": not validation_errors,
                    "validation_errors": validation_errors,
                },
            )
        )
        return validation_errors

    def list_source_references(self, package: GroundedTeachingPackage) -> list[SourceReference]:
        return list(package.source_references)

    def _build_primary_evidence(self, concept: ContextConceptSnapshot) -> PrimaryEvidence:
        return PrimaryEvidence(
            source_reference=SourceReference(
                academic_object_type="content_concept",
                object_id=concept.content_concept_id,
                title=concept.content_concept_title,
                relationship="primary_concept",
                sequence_number=concept.sequence_number,
            ),
            title=concept.content_concept_title,
            description=concept.content_concept_description,
            learning_objective=concept.content_concept_learning_objective,
            review_status=concept.review_status,
            quality_status=concept.quality_status,
        )

    def _build_supporting_evidence(self, concept: ContextConceptSnapshot) -> list[SupportingEvidence]:
        section = concept.content_section
        if section is None:
            return []

        evidence = [self._build_section_evidence(section)]
        resource = section.learning_resource
        if resource is not None:
            evidence.append(self._build_resource_evidence(resource))
            curriculum = resource.curriculum
            if curriculum.curriculum_id is not None:
                evidence.append(self._build_curriculum_evidence(curriculum))
            if curriculum.curriculum_unit_id is not None:
                evidence.append(self._build_curriculum_unit_evidence(curriculum))
            if resource.subject_id is not None:
                evidence.append(self._build_subject_evidence(resource))
        return evidence

    def _build_section_evidence(self, section: ContextSectionSnapshot) -> SupportingEvidence:
        return SupportingEvidence(
            source_reference=SourceReference(
                academic_object_type="content_section",
                object_id=section.content_section_id,
                title=section.content_section_title,
                relationship="parent_section",
                sequence_number=section.sequence_number,
            ),
            title=section.content_section_title,
            evidence_type="parent_section",
            review_status=section.review_status,
            quality_status=section.quality_status,
        )

    def _build_resource_evidence(self, resource: ContextResourceSnapshot) -> SupportingEvidence:
        return SupportingEvidence(
            source_reference=SourceReference(
                academic_object_type="learning_resource",
                object_id=resource.learning_resource_id,
                title=resource.learning_resource_title,
                relationship="source_resource",
            ),
            title=resource.learning_resource_title,
            evidence_type="source_resource",
            metadata={"resource_type": resource.resource_type},
        )

    def _build_curriculum_evidence(self, curriculum: ContextCurriculumSnapshot) -> SupportingEvidence:
        return SupportingEvidence(
            source_reference=SourceReference(
                academic_object_type="curriculum",
                object_id=curriculum.curriculum_id or "",
                title=curriculum.curriculum_name or "",
                relationship="curriculum",
            ),
            title=curriculum.curriculum_name or "",
            evidence_type="curriculum",
        )

    def _build_curriculum_unit_evidence(self, curriculum: ContextCurriculumSnapshot) -> SupportingEvidence:
        return SupportingEvidence(
            source_reference=SourceReference(
                academic_object_type="curriculum_unit",
                object_id=curriculum.curriculum_unit_id or "",
                title=curriculum.curriculum_unit_title or "",
                relationship="curriculum_unit",
                sequence_number=curriculum.curriculum_unit_sequence_number,
            ),
            title=curriculum.curriculum_unit_title or "",
            evidence_type="curriculum_unit",
        )

    def _build_subject_evidence(self, resource: ContextResourceSnapshot) -> SupportingEvidence:
        return SupportingEvidence(
            source_reference=SourceReference(
                academic_object_type="subject",
                object_id=resource.subject_id or "",
                title=resource.subject_name or "",
                relationship="subject",
            ),
            title=resource.subject_name or "",
            evidence_type="subject",
        )

    def _calculate_grounding_confidence(
        self,
        primary_evidence: PrimaryEvidence,
        supporting_evidence: list[SupportingEvidence],
    ) -> float:
        if primary_evidence.review_status == "approved" and primary_evidence.quality_status in {"acceptable", "high"}:
            return 1.0
        if supporting_evidence:
            return 0.75
        return 0.5

    def _content_concept_id(self, package: GroundedTeachingPackage) -> str | None:
        if package.primary_concept is None:
            return None
        return package.primary_concept.content_concept_id
