from __future__ import annotations

from typing import Any, Optional

from apps.academic.domain.models import Curriculum, CurriculumUnit, Subject
from apps.core.events import BusinessEvent, EventPublisher


class CurriculumService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def create_curriculum(self, subject: Subject, name: str, version: str = "1.0", description: str = "", institution=None, is_active: bool = True) -> Curriculum:
        curriculum = Curriculum.objects.create(
            subject=subject,
            institution=institution,
            name=name,
            description=description,
            version=version,
            is_active=is_active,
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.curriculum_created",
                payload={
                    "curriculum_id": str(curriculum.id),
                    "subject_id": str(subject.id),
                    "institution_id": str(institution.id) if institution else None,
                    "name": curriculum.name,
                    "version": curriculum.version,
                },
            )
        )
        return curriculum

    def update_curriculum(self, curriculum: Curriculum, **kwargs: Any) -> Curriculum:
        for field, value in kwargs.items():
            setattr(curriculum, field, value)
        curriculum.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.curriculum_updated",
                payload={
                    "curriculum_id": str(curriculum.id),
                    "subject_id": str(curriculum.subject_id),
                    "institution_id": str(curriculum.institution_id) if curriculum.institution_id else None,
                    "name": curriculum.name,
                    "version": curriculum.version,
                },
            )
        )
        return curriculum

    def archive_curriculum(self, curriculum: Curriculum) -> Curriculum:
        curriculum.is_active = False
        curriculum.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.curriculum_archived",
                payload={
                    "curriculum_id": str(curriculum.id),
                    "subject_id": str(curriculum.subject_id),
                    "institution_id": str(curriculum.institution_id) if curriculum.institution_id else None,
                },
            )
        )
        return curriculum

    def get_curriculum(self, subject: Subject, curriculum_id: str) -> Curriculum:
        return Curriculum.objects.get(subject=subject, id=curriculum_id)

    def list_curricula(self, subject: Subject) -> list[Curriculum]:
        return list(Curriculum.objects.filter(subject=subject).order_by("name", "version"))

    def create_unit(self, curriculum: Curriculum, title: str, sequence_number: int, description: str = "", is_active: bool = True) -> CurriculumUnit:
        unit = CurriculumUnit.objects.create(
            curriculum=curriculum,
            title=title,
            description=description,
            sequence_number=sequence_number,
            is_active=is_active,
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.curriculum_unit_created",
                payload={
                    "curriculum_unit_id": str(unit.id),
                    "curriculum_id": str(curriculum.id),
                    "title": unit.title,
                    "sequence_number": unit.sequence_number,
                },
            )
        )
        return unit

    def update_unit(self, unit: CurriculumUnit, **kwargs: Any) -> CurriculumUnit:
        for field, value in kwargs.items():
            setattr(unit, field, value)
        unit.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.curriculum_unit_updated",
                payload={
                    "curriculum_unit_id": str(unit.id),
                    "curriculum_id": str(unit.curriculum_id),
                    "title": unit.title,
                    "sequence_number": unit.sequence_number,
                },
            )
        )
        return unit

    def archive_unit(self, unit: CurriculumUnit) -> CurriculumUnit:
        unit.is_active = False
        unit.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.curriculum_unit_archived",
                payload={
                    "curriculum_unit_id": str(unit.id),
                    "curriculum_id": str(unit.curriculum_id),
                    "sequence_number": unit.sequence_number,
                },
            )
        )
        return unit

    def list_units(self, curriculum: Curriculum) -> list[CurriculumUnit]:
        return list(CurriculumUnit.objects.filter(curriculum=curriculum).order_by("sequence_number"))
