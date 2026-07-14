from __future__ import annotations

from typing import Any, Optional

from apps.academic.domain.models import ContentConcept, ContentSection, LearningResource
from apps.core.events import BusinessEvent, EventPublisher


class LearningContentService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def create_section(self, learning_resource: LearningResource, title: str, sequence_number: int, description: str = "", is_active: bool = True) -> ContentSection:
        section = ContentSection.objects.create(
            learning_resource=learning_resource,
            title=title,
            description=description,
            sequence_number=sequence_number,
            is_active=is_active,
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.content_section_created",
                payload={
                    "section_id": str(section.id),
                    "learning_resource_id": str(learning_resource.id),
                    "title": section.title,
                    "sequence_number": section.sequence_number,
                },
            )
        )
        return section

    def update_section(self, section: ContentSection, **kwargs: Any) -> ContentSection:
        for field, value in kwargs.items():
            setattr(section, field, value)
        section.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.content_section_updated",
                payload={
                    "section_id": str(section.id),
                    "learning_resource_id": str(section.learning_resource_id),
                    "title": section.title,
                    "sequence_number": section.sequence_number,
                },
            )
        )
        return section

    def archive_section(self, section: ContentSection) -> ContentSection:
        section.is_active = False
        section.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.content_section_archived",
                payload={"section_id": str(section.id), "learning_resource_id": str(section.learning_resource_id)},
            )
        )
        return section

    def delete_section(self, section: ContentSection) -> None:
        payload = {
            "section_id": str(section.id),
            "learning_resource_id": str(section.learning_resource_id),
            "title": section.title,
        }
        section.delete()
        self.event_publisher.publish(BusinessEvent.create("academic.content_section_deleted", payload=payload))

    def get_section(self, learning_resource: LearningResource, section_id: str) -> ContentSection:
        return ContentSection.objects.get(learning_resource=learning_resource, id=section_id)

    def list_sections(self, learning_resource: LearningResource) -> list[ContentSection]:
        return list(ContentSection.objects.filter(learning_resource=learning_resource).order_by("sequence_number"))

    def create_concept(self, content_section: ContentSection, title: str, sequence_number: int, description: str = "", learning_objective: str = "", is_active: bool = True) -> ContentConcept:
        concept = ContentConcept.objects.create(
            content_section=content_section,
            title=title,
            description=description,
            learning_objective=learning_objective,
            sequence_number=sequence_number,
            is_active=is_active,
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.content_concept_created",
                payload={
                    "concept_id": str(concept.id),
                    "section_id": str(content_section.id),
                    "title": concept.title,
                    "sequence_number": concept.sequence_number,
                },
            )
        )
        return concept

    def update_concept(self, concept: ContentConcept, **kwargs: Any) -> ContentConcept:
        for field, value in kwargs.items():
            setattr(concept, field, value)
        concept.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.content_concept_updated",
                payload={
                    "concept_id": str(concept.id),
                    "section_id": str(concept.content_section_id),
                    "title": concept.title,
                    "sequence_number": concept.sequence_number,
                },
            )
        )
        return concept

    def archive_concept(self, concept: ContentConcept) -> ContentConcept:
        concept.is_active = False
        concept.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.content_concept_archived",
                payload={"concept_id": str(concept.id), "section_id": str(concept.content_section_id)},
            )
        )
        return concept

    def delete_concept(self, concept: ContentConcept) -> None:
        payload = {
            "concept_id": str(concept.id),
            "section_id": str(concept.content_section_id),
            "title": concept.title,
        }
        concept.delete()
        self.event_publisher.publish(BusinessEvent.create("academic.content_concept_deleted", payload=payload))

    def get_concept(self, content_section: ContentSection, concept_id: str) -> ContentConcept:
        return ContentConcept.objects.get(content_section=content_section, id=concept_id)

    def list_concepts(self, content_section: ContentSection) -> list[ContentConcept]:
        return list(ContentConcept.objects.filter(content_section=content_section).order_by("sequence_number"))
