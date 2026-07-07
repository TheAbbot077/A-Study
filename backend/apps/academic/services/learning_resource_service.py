from __future__ import annotations

from typing import Any, Optional

from apps.academic.domain.models import Curriculum, CurriculumUnit, LearningResource, Subject
from apps.core.events import BusinessEvent, EventPublisher


class LearningResourceService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def create_resource(
        self,
        subject: Subject,
        title: str,
        resource_type: str = LearningResource.ResourceType.OTHER,
        description: str = "",
        institution=None,
        curriculum: Optional[Curriculum] = None,
        curriculum_unit: Optional[CurriculumUnit] = None,
        stored_file=None,
        status: str = LearningResource.Status.DRAFT,
        source_label: str = "",
    ) -> LearningResource:
        resource = LearningResource.objects.create(
            institution=institution,
            subject=subject,
            curriculum=curriculum,
            curriculum_unit=curriculum_unit,
            stored_file=stored_file,
            title=title,
            description=description,
            resource_type=resource_type,
            status=status,
            source_label=source_label,
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.learning_resource_created",
                payload={
                    "resource_id": str(resource.id),
                    "subject_id": str(subject.id),
                    "title": resource.title,
                    "resource_type": resource.resource_type,
                    "status": resource.status,
                },
            )
        )
        return resource

    def update_resource(self, resource: LearningResource, **kwargs: Any) -> LearningResource:
        for field, value in kwargs.items():
            setattr(resource, field, value)
        resource.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.learning_resource_updated",
                payload={
                    "resource_id": str(resource.id),
                    "title": resource.title,
                    "resource_type": resource.resource_type,
                    "status": resource.status,
                },
            )
        )
        return resource

    def activate_resource(self, resource: LearningResource) -> LearningResource:
        resource.status = LearningResource.Status.ACTIVE
        resource.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.learning_resource_activated",
                payload={"resource_id": str(resource.id), "title": resource.title},
            )
        )
        return resource

    def archive_resource(self, resource: LearningResource) -> LearningResource:
        resource.status = LearningResource.Status.ARCHIVED
        resource.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.learning_resource_archived",
                payload={"resource_id": str(resource.id), "title": resource.title},
            )
        )
        return resource

    def get_resource(self, subject: Subject, resource_id: str) -> LearningResource:
        return LearningResource.objects.get(subject=subject, id=resource_id)

    def list_resources(self, subject: Optional[Subject] = None, curriculum: Optional[Curriculum] = None, curriculum_unit: Optional[CurriculumUnit] = None, status: Optional[str] = None, resource_type: Optional[str] = None):
        qs = LearningResource.objects.all()
        if subject is not None:
            qs = qs.filter(subject=subject)
        if curriculum is not None:
            qs = qs.filter(curriculum=curriculum)
        if curriculum_unit is not None:
            qs = qs.filter(curriculum_unit=curriculum_unit)
        if status is not None:
            qs = qs.filter(status=status)
        if resource_type is not None:
            qs = qs.filter(resource_type=resource_type)
        return list(qs.order_by("-created_at"))
