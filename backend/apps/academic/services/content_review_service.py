from __future__ import annotations

from typing import Any, Optional

from django.utils import timezone

from apps.academic.domain.models import ContentConcept, ContentSection
from apps.core.events import BusinessEvent, EventPublisher


class ContentReviewService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def submit_section_for_review(self, section: ContentSection, submitted_by=None, notes: Optional[str] = None) -> ContentSection:
        section.review_status = ContentSection.ReviewStatus.IN_REVIEW
        self._apply_notes(section, notes)
        section.save()
        self._publish_section_event(
            "academic.content_section_submitted_for_review",
            section,
            actor=submitted_by,
        )
        return section

    def approve_section(self, section: ContentSection, approved_by, notes: Optional[str] = None) -> ContentSection:
        section.review_status = ContentSection.ReviewStatus.APPROVED
        section.approved_at = timezone.now()
        section.approved_by = approved_by
        self._apply_notes(section, notes)
        section.save()
        self._publish_section_event(
            "academic.content_section_approved",
            section,
            actor=approved_by,
        )
        return section

    def reject_section(self, section: ContentSection, rejected_by, notes: Optional[str] = None) -> ContentSection:
        section.review_status = ContentSection.ReviewStatus.REJECTED
        section.approved_at = None
        section.approved_by = None
        self._apply_notes(section, notes)
        section.save()
        self._publish_section_event(
            "academic.content_section_rejected",
            section,
            actor=rejected_by,
        )
        return section

    def mark_section_quality(
        self,
        section: ContentSection,
        quality_status: str,
        marked_by=None,
        notes: Optional[str] = None,
    ) -> ContentSection:
        self._validate_choice(quality_status, ContentSection.QualityStatus.values, "quality_status")
        section.quality_status = quality_status
        self._apply_notes(section, notes)
        section.save()
        self._publish_section_event(
            "academic.content_section_quality_marked",
            section,
            actor=marked_by,
            extra_payload={"quality_status": section.quality_status},
        )
        return section

    def submit_concept_for_review(self, concept: ContentConcept, submitted_by=None, notes: Optional[str] = None) -> ContentConcept:
        concept.review_status = ContentConcept.ReviewStatus.IN_REVIEW
        self._apply_notes(concept, notes)
        concept.save()
        self._publish_concept_event(
            "academic.content_concept_submitted_for_review",
            concept,
            actor=submitted_by,
        )
        return concept

    def approve_concept(self, concept: ContentConcept, approved_by, notes: Optional[str] = None) -> ContentConcept:
        concept.review_status = ContentConcept.ReviewStatus.APPROVED
        concept.approved_at = timezone.now()
        concept.approved_by = approved_by
        self._apply_notes(concept, notes)
        concept.save()
        self._publish_concept_event(
            "academic.content_concept_approved",
            concept,
            actor=approved_by,
        )
        return concept

    def reject_concept(self, concept: ContentConcept, rejected_by, notes: Optional[str] = None) -> ContentConcept:
        concept.review_status = ContentConcept.ReviewStatus.REJECTED
        concept.approved_at = None
        concept.approved_by = None
        self._apply_notes(concept, notes)
        concept.save()
        self._publish_concept_event(
            "academic.content_concept_rejected",
            concept,
            actor=rejected_by,
        )
        return concept

    def mark_concept_quality(
        self,
        concept: ContentConcept,
        quality_status: str,
        marked_by=None,
        notes: Optional[str] = None,
    ) -> ContentConcept:
        self._validate_choice(quality_status, ContentConcept.QualityStatus.values, "quality_status")
        concept.quality_status = quality_status
        self._apply_notes(concept, notes)
        concept.save()
        self._publish_concept_event(
            "academic.content_concept_quality_marked",
            concept,
            actor=marked_by,
            extra_payload={"quality_status": concept.quality_status},
        )
        return concept

    def _apply_notes(self, content_item, notes: Optional[str]) -> None:
        if notes is not None:
            content_item.review_notes = notes

    def _validate_choice(self, value: str, allowed_values: list[str], field_name: str) -> None:
        if value not in allowed_values:
            allowed = ", ".join(allowed_values)
            raise ValueError(f"Invalid {field_name}: {value}. Expected one of: {allowed}")

    def _publish_section_event(
        self,
        event_name: str,
        section: ContentSection,
        actor=None,
        extra_payload: Optional[dict[str, Any]] = None,
    ) -> None:
        payload = {
            "section_id": str(section.id),
            "learning_resource_id": str(section.learning_resource_id),
            "review_status": section.review_status,
            "quality_status": section.quality_status,
            "actor_id": str(actor.id) if actor is not None else None,
        }
        payload.update(extra_payload or {})
        self.event_publisher.publish(BusinessEvent.create(event_name, payload=payload))

    def _publish_concept_event(
        self,
        event_name: str,
        concept: ContentConcept,
        actor=None,
        extra_payload: Optional[dict[str, Any]] = None,
    ) -> None:
        payload = {
            "concept_id": str(concept.id),
            "section_id": str(concept.content_section_id),
            "review_status": concept.review_status,
            "quality_status": concept.quality_status,
            "actor_id": str(actor.id) if actor is not None else None,
        }
        payload.update(extra_payload or {})
        self.event_publisher.publish(BusinessEvent.create(event_name, payload=payload))
