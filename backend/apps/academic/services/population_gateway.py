from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from django.core.exceptions import ValidationError

from apps.academic.domain.models import ContentConcept, ContentSection, LearningResource, Subject


@dataclass(frozen=True)
class PopulateSectionSpecification:
    stable_source_key: str
    title: str
    description: str
    sequence_number: int


@dataclass(frozen=True)
class PopulateConceptSpecification:
    stable_source_key: str
    parent_section_source_key: str
    title: str
    description: str
    learning_objective: str
    sequence_number: int


@dataclass(frozen=True)
class PopulationItemResult:
    academic_id: UUID
    outcome: str


class AcademicPopulationGateway(Protocol):
    def validate_target(self, *, resource_id: UUID, subject_id: UUID) -> bool: ...
    def populate_section(self, *, resource_id: UUID, specification: PopulateSectionSpecification) -> PopulationItemResult: ...
    def populate_concept(self, *, academic_section_id: UUID, specification: PopulateConceptSpecification) -> PopulationItemResult: ...


class DjangoAcademicPopulationGateway:
    """Academic-owned application boundary for controlled projection materialization."""

    def validate_target(self, *, resource_id, subject_id):
        return LearningResource.objects.filter(id=resource_id, subject_id=subject_id).exists() and Subject.objects.filter(id=subject_id, is_active=True).exists()

    def populate_section(self, *, resource_id, specification):
        if ContentSection.objects.filter(learning_resource_id=resource_id, sequence_number=specification.sequence_number).exists():
            raise ValidationError("The requested section position is occupied by unrelated academic content.", code="population_conflict")
        section = ContentSection.objects.create(
            learning_resource_id=resource_id, title=specification.title,
            description=specification.description, sequence_number=specification.sequence_number,
        )
        return PopulationItemResult(section.id, "created")

    def populate_concept(self, *, academic_section_id, specification):
        if ContentConcept.objects.filter(content_section_id=academic_section_id, sequence_number=specification.sequence_number).exists():
            raise ValidationError("The requested concept position is occupied by unrelated academic content.", code="population_conflict")
        concept = ContentConcept.objects.create(
            content_section_id=academic_section_id, title=specification.title,
            description=specification.description, learning_objective=specification.learning_objective,
            sequence_number=specification.sequence_number,
        )
        return PopulationItemResult(concept.id, "created")
