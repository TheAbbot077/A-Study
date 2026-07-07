from __future__ import annotations

from typing import Any, Optional

from django.db import transaction

from apps.academic.domain.models import ContentConcept, ContentSection, LearningResource
from apps.core.events import BusinessEvent, EventPublisher


def _validate_sequence_number(sequence_number: int, label: str) -> None:
    if sequence_number < 1:
        raise ValueError(f"{label} sequence_number must be greater than or equal to 1")


class ManualAuthoringService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def create_section(
        self,
        learning_resource: LearningResource,
        title: str,
        sequence_number: int,
        description: str = "",
        is_active: bool = True,
    ) -> ContentSection:
        _validate_sequence_number(sequence_number, "section")
        section = ContentSection.objects.create(
            learning_resource=learning_resource,
            title=title,
            description=description,
            sequence_number=sequence_number,
            is_active=is_active,
        )
        self._publish_section_event("academic.manual_section_created", section)
        return section

    def update_section(self, section: ContentSection, **kwargs: Any) -> ContentSection:
        if "sequence_number" in kwargs:
            _validate_sequence_number(kwargs["sequence_number"], "section")

        for field, value in kwargs.items():
            setattr(section, field, value)

        section.save()
        self._publish_section_event("academic.manual_section_updated", section)
        return section

    def archive_section(self, section: ContentSection) -> ContentSection:
        section.is_active = False
        section.save()
        self._publish_section_event("academic.manual_section_archived", section)
        return section

    def reorder_section(self, section: ContentSection, new_sequence_number: int) -> ContentSection:
        _validate_sequence_number(new_sequence_number, "section")
        old_sequence_number = section.sequence_number

        with transaction.atomic():
            conflicting_section = (
                ContentSection.objects.select_for_update()
                .filter(learning_resource_id=section.learning_resource_id, sequence_number=new_sequence_number)
                .exclude(id=section.id)
                .first()
            )

            if conflicting_section is not None:
                section.sequence_number = self._next_section_sequence_number(section.learning_resource_id)
                section.save()
                conflicting_section.sequence_number = old_sequence_number
                conflicting_section.save()

            section.sequence_number = new_sequence_number
            section.save()

        self._publish_section_event(
            "academic.manual_section_reordered",
            section,
            extra_payload={"old_sequence_number": old_sequence_number},
        )
        return section

    def create_concept(
        self,
        content_section: ContentSection,
        title: str,
        sequence_number: int,
        description: str = "",
        learning_objective: str = "",
        is_active: bool = True,
    ) -> ContentConcept:
        _validate_sequence_number(sequence_number, "concept")
        concept = ContentConcept.objects.create(
            content_section=content_section,
            title=title,
            description=description,
            learning_objective=learning_objective,
            sequence_number=sequence_number,
            is_active=is_active,
        )
        self._publish_concept_event("academic.manual_concept_created", concept)
        return concept

    def update_concept(self, concept: ContentConcept, **kwargs: Any) -> ContentConcept:
        if "sequence_number" in kwargs:
            _validate_sequence_number(kwargs["sequence_number"], "concept")

        for field, value in kwargs.items():
            setattr(concept, field, value)

        concept.save()
        self._publish_concept_event("academic.manual_concept_updated", concept)
        return concept

    def archive_concept(self, concept: ContentConcept) -> ContentConcept:
        concept.is_active = False
        concept.save()
        self._publish_concept_event("academic.manual_concept_archived", concept)
        return concept

    def reorder_concept(self, concept: ContentConcept, new_sequence_number: int) -> ContentConcept:
        _validate_sequence_number(new_sequence_number, "concept")
        old_sequence_number = concept.sequence_number

        with transaction.atomic():
            conflicting_concept = (
                ContentConcept.objects.select_for_update()
                .filter(content_section_id=concept.content_section_id, sequence_number=new_sequence_number)
                .exclude(id=concept.id)
                .first()
            )

            if conflicting_concept is not None:
                concept.sequence_number = self._next_concept_sequence_number(concept.content_section_id)
                concept.save()
                conflicting_concept.sequence_number = old_sequence_number
                conflicting_concept.save()

            concept.sequence_number = new_sequence_number
            concept.save()

        self._publish_concept_event(
            "academic.manual_concept_reordered",
            concept,
            extra_payload={"old_sequence_number": old_sequence_number},
        )
        return concept

    def _next_section_sequence_number(self, learning_resource_id: str) -> int:
        last_section = (
            ContentSection.objects.filter(learning_resource_id=learning_resource_id)
            .order_by("-sequence_number")
            .first()
        )
        return (last_section.sequence_number if last_section else 0) + 1

    def _next_concept_sequence_number(self, content_section_id: str) -> int:
        last_concept = (
            ContentConcept.objects.filter(content_section_id=content_section_id)
            .order_by("-sequence_number")
            .first()
        )
        return (last_concept.sequence_number if last_concept else 0) + 1

    def _publish_section_event(
        self,
        event_name: str,
        section: ContentSection,
        extra_payload: Optional[dict[str, Any]] = None,
    ) -> None:
        payload = {
            "section_id": str(section.id),
            "learning_resource_id": str(section.learning_resource_id),
            "title": section.title,
            "sequence_number": section.sequence_number,
        }
        payload.update(extra_payload or {})
        self.event_publisher.publish(BusinessEvent.create(event_name, payload=payload))

    def _publish_concept_event(
        self,
        event_name: str,
        concept: ContentConcept,
        extra_payload: Optional[dict[str, Any]] = None,
    ) -> None:
        payload = {
            "concept_id": str(concept.id),
            "section_id": str(concept.content_section_id),
            "title": concept.title,
            "sequence_number": concept.sequence_number,
        }
        payload.update(extra_payload or {})
        self.event_publisher.publish(BusinessEvent.create(event_name, payload=payload))
