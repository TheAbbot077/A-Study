from __future__ import annotations

from typing import Any, Optional

from apps.academic.domain.models import ContentConcept
from apps.core.exceptions import DomainValidationError
from apps.assessments.domain.models import (
    Assessment,
    AssessmentItemBankLink,
    AssessmentItemType,
    ItemBankEntry,
    ItemDifficulty,
    ItemOption,
    ItemQualityStatus,
    ItemReviewStatus,
)
from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import User


class ItemBankService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def create_item(
        self,
        content_concept: ContentConcept,
        item_type: str,
        prompt: str,
        explanation: str = "",
        difficulty: str = ItemDifficulty.UNKNOWN,
        authored_by: Optional[User] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ItemBankEntry:
        self._validate_item_type(item_type)
        self._validate_difficulty(difficulty)
        item = ItemBankEntry.objects.create(
            content_concept=content_concept,
            item_type=item_type,
            prompt=prompt,
            explanation=explanation,
            difficulty=difficulty,
            review_status=ItemReviewStatus.DRAFT,
            quality_status=ItemQualityStatus.UNKNOWN,
            authored_by=authored_by,
            metadata=metadata or {},
        )
        self._publish_item_event("assessment.item_bank_entry_created", item)
        return item

    def update_item(
        self,
        item: ItemBankEntry,
        item_type: Optional[str] = None,
        prompt: Optional[str] = None,
        explanation: Optional[str] = None,
        difficulty: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ItemBankEntry:
        if item_type is not None:
            self._validate_item_type(item_type)
            item.item_type = item_type
        if prompt is not None:
            item.prompt = prompt
        if explanation is not None:
            item.explanation = explanation
        if difficulty is not None:
            self._validate_difficulty(difficulty)
            item.difficulty = difficulty
        if metadata is not None:
            item.metadata = metadata
        item.save()
        self._publish_item_event("assessment.item_bank_entry_updated", item)
        return item

    def archive_item(self, item: ItemBankEntry) -> ItemBankEntry:
        item.review_status = ItemReviewStatus.ARCHIVED
        item.save()
        self._publish_item_event("assessment.item_bank_entry_archived", item)
        return item

    def submit_item_for_review(self, item: ItemBankEntry) -> ItemBankEntry:
        item.review_status = ItemReviewStatus.IN_REVIEW
        item.save()
        self._publish_item_event("assessment.item_bank_entry_submitted_for_review", item)
        return item

    def approve_item(self, item: ItemBankEntry) -> ItemBankEntry:
        item.review_status = ItemReviewStatus.APPROVED
        item.save()
        self._publish_item_event("assessment.item_bank_entry_approved", item)
        return item

    def reject_item(self, item: ItemBankEntry) -> ItemBankEntry:
        item.review_status = ItemReviewStatus.REJECTED
        item.save()
        self._publish_item_event("assessment.item_bank_entry_rejected", item)
        return item

    def mark_item_quality(self, item: ItemBankEntry, quality_status: str) -> ItemBankEntry:
        self._validate_quality_status(quality_status)
        item.quality_status = quality_status
        item.save()
        self._publish_item_event("assessment.item_bank_entry_quality_marked", item)
        return item

    def add_option(
        self,
        item: ItemBankEntry,
        label: str,
        content: str,
        sequence_number: int,
        is_correct: bool = False,
        explanation: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> ItemOption:
        self._validate_sequence_number(sequence_number, "Item option")
        if ItemOption.objects.filter(item_bank_entry=item, sequence_number=sequence_number).exists():
            raise DomainValidationError("Item option sequence_number must be unique for the item bank entry.")
        option = ItemOption.objects.create(
            item_bank_entry=item,
            label=label,
            content=content,
            is_correct=is_correct,
            explanation=explanation,
            sequence_number=sequence_number,
            metadata=metadata or {},
        )
        self._publish_option_event("assessment.item_option_added", option)
        return option

    def update_option(
        self,
        option: ItemOption,
        label: Optional[str] = None,
        content: Optional[str] = None,
        is_correct: Optional[bool] = None,
        explanation: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ItemOption:
        if label is not None:
            option.label = label
        if content is not None:
            option.content = content
        if is_correct is not None:
            option.is_correct = is_correct
        if explanation is not None:
            option.explanation = explanation
        if metadata is not None:
            option.metadata = metadata
        option.save()
        self._publish_option_event("assessment.item_option_updated", option)
        return option

    def remove_option(self, option: ItemOption) -> None:
        payload = self._option_payload(option)
        option.delete()
        self.event_publisher.publish(BusinessEvent.create("assessment.item_option_removed", payload=payload))

    def list_items_for_concept(self, content_concept: ContentConcept) -> list[ItemBankEntry]:
        return list(ItemBankEntry.objects.filter(content_concept=content_concept).order_by("-created_at"))

    def add_item_to_assessment(
        self,
        assessment: Assessment,
        item: ItemBankEntry,
        sequence_number: int,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AssessmentItemBankLink:
        self._validate_sequence_number(sequence_number, "Assessment item bank link")
        if AssessmentItemBankLink.objects.filter(assessment=assessment, item_bank_entry=item).exists():
            raise DomainValidationError("Item bank entry is already linked to this assessment.")
        if AssessmentItemBankLink.objects.filter(assessment=assessment, sequence_number=sequence_number).exists():
            raise DomainValidationError("Assessment item bank link sequence_number must be unique for the assessment.")
        link = AssessmentItemBankLink.objects.create(
            assessment=assessment,
            item_bank_entry=item,
            sequence_number=sequence_number,
            metadata=metadata or {},
        )
        self._publish_link_event("assessment.item_added_to_assessment", link)
        return link

    def remove_item_from_assessment(self, link: AssessmentItemBankLink) -> None:
        payload = self._link_payload(link)
        link.delete()
        self.event_publisher.publish(BusinessEvent.create("assessment.item_removed_from_assessment", payload=payload))

    def list_items_for_assessment(self, assessment: Assessment) -> list[AssessmentItemBankLink]:
        return list(AssessmentItemBankLink.objects.filter(assessment=assessment).order_by("sequence_number"))

    def _validate_item_type(self, item_type: str) -> None:
        if item_type not in AssessmentItemType.values:
            raise DomainValidationError(f"Unsupported assessment item type: {item_type}.")

    def _validate_difficulty(self, difficulty: str) -> None:
        if difficulty not in ItemDifficulty.values:
            raise DomainValidationError(f"Unsupported item difficulty: {difficulty}.")

    def _validate_quality_status(self, quality_status: str) -> None:
        if quality_status not in ItemQualityStatus.values:
            raise DomainValidationError(f"Unsupported item quality status: {quality_status}.")

    def _validate_sequence_number(self, sequence_number: int, label: str) -> None:
        if sequence_number < 1:
            raise DomainValidationError(f"{label} sequence_number must be greater than or equal to 1.")

    def _publish_item_event(self, event_name: str, item: ItemBankEntry) -> None:
        self.event_publisher.publish(BusinessEvent.create(event_name, payload=self._item_payload(item)))

    def _publish_option_event(self, event_name: str, option: ItemOption) -> None:
        self.event_publisher.publish(BusinessEvent.create(event_name, payload=self._option_payload(option)))

    def _publish_link_event(self, event_name: str, link: AssessmentItemBankLink) -> None:
        self.event_publisher.publish(BusinessEvent.create(event_name, payload=self._link_payload(link)))

    def _item_payload(self, item: ItemBankEntry) -> dict[str, Any]:
        return {
            "item_bank_entry_id": str(item.id),
            "content_concept_id": str(item.content_concept_id),
            "item_type": item.item_type,
            "difficulty": item.difficulty,
            "review_status": item.review_status,
            "quality_status": item.quality_status,
        }

    def _option_payload(self, option: ItemOption) -> dict[str, Any]:
        return {
            "item_option_id": str(option.id),
            "item_bank_entry_id": str(option.item_bank_entry_id),
            "sequence_number": option.sequence_number,
            "is_correct": option.is_correct,
        }

    def _link_payload(self, link: AssessmentItemBankLink) -> dict[str, Any]:
        return {
            "assessment_item_bank_link_id": str(link.id),
            "assessment_id": str(link.assessment_id),
            "item_bank_entry_id": str(link.item_bank_entry_id),
            "sequence_number": link.sequence_number,
        }
