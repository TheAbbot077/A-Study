from __future__ import annotations

from typing import Any, Optional

from apps.academic.domain.models import Subject
from apps.core.events import BusinessEvent, EventPublisher


class AcademicStructureService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def create_subject(self, institution, code: str, name: str, description: str = "", is_active: bool = True) -> Subject:
        subject = Subject.objects.create(
            institution=institution,
            code=code,
            name=name,
            description=description,
            is_active=is_active,
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.subject_created",
                payload={
                    "subject_id": str(subject.id),
                    "institution_id": str(institution.id),
                    "code": subject.code,
                    "name": subject.name,
                },
            )
        )
        return subject

    def update_subject(self, subject: Subject, **kwargs: Any) -> Subject:
        persisted = Subject.objects.filter(id=subject.id).first()
        if persisted is None:
            persisted = subject

        for field, value in kwargs.items():
            setattr(persisted, field, value)

        persisted.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.subject_updated",
                payload={
                    "subject_id": str(persisted.id),
                    "institution_id": str(persisted.institution_id),
                    "code": persisted.code,
                    "name": persisted.name,
                },
            )
        )
        return persisted

    def archive_subject(self, subject: Subject) -> Subject:
        persisted = Subject.objects.filter(id=subject.id).first()
        if persisted is None:
            persisted = subject

        persisted.is_active = False
        persisted.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.subject_archived",
                payload={
                    "subject_id": str(persisted.id),
                    "institution_id": str(persisted.institution_id),
                    "code": persisted.code,
                },
            )
        )
        return persisted

    def list_subjects(self, institution) -> list[Subject]:
        return list(Subject.objects.filter(institution=institution).order_by("code"))

    def get_subject(self, institution, subject_id: str) -> Subject:
        return Subject.objects.get(institution=institution, id=subject_id)
