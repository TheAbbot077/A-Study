from unittest.mock import Mock, patch

from django.db import models
from django.test import SimpleTestCase

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
from apps.assessments.services import ItemBankService
from apps.core.events import default_event_registry


class DummyContentConcept:
    id = "concept-1"


class DummyUser:
    id = "user-1"


class ItemBankServiceTests(SimpleTestCase):
    def test_item_creation(self):
        publisher = Mock()
        service = ItemBankService(event_publisher=publisher)
        concept = DummyContentConcept()
        author = DummyUser()

        with patch("apps.assessments.services.item_bank_service.ItemBankEntry.objects") as entry_objects:
            fake_item = self._item()
            entry_objects.create.return_value = fake_item

            item = service.create_item(
                concept,
                AssessmentItemType.MULTIPLE_CHOICE,
                "Which statement is correct?",
                authored_by=author,
            )

        self.assertIs(item, fake_item)
        entry_objects.create.assert_called_once_with(
            content_concept=concept,
            item_type=AssessmentItemType.MULTIPLE_CHOICE,
            prompt="Which statement is correct?",
            explanation="",
            difficulty=ItemDifficulty.UNKNOWN,
            review_status=ItemReviewStatus.DRAFT,
            quality_status=ItemQualityStatus.UNKNOWN,
            authored_by=author,
            metadata={},
        )
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.item_bank_entry_created")

    def test_item_update(self):
        publisher = Mock()
        service = ItemBankService(event_publisher=publisher)
        item = self._item()

        updated = service.update_item(
            item,
            prompt="Updated prompt",
            explanation="Updated explanation",
            difficulty=ItemDifficulty.HARD,
            metadata={"source": "manual"},
        )

        self.assertIs(updated, item)
        self.assertEqual(item.prompt, "Updated prompt")
        self.assertEqual(item.explanation, "Updated explanation")
        self.assertEqual(item.difficulty, ItemDifficulty.HARD)
        item.save.assert_called_once()
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.item_bank_entry_updated")

    def test_item_archive(self):
        item = self._item()

        ItemBankService(event_publisher=Mock()).archive_item(item)

        self.assertEqual(item.review_status, ItemReviewStatus.ARCHIVED)
        item.save.assert_called_once()

    def test_submit_item_for_review(self):
        item = self._item()

        ItemBankService(event_publisher=Mock()).submit_item_for_review(item)

        self.assertEqual(item.review_status, ItemReviewStatus.IN_REVIEW)
        item.save.assert_called_once()

    def test_approve_item(self):
        item = self._item()

        ItemBankService(event_publisher=Mock()).approve_item(item)

        self.assertEqual(item.review_status, ItemReviewStatus.APPROVED)
        item.save.assert_called_once()

    def test_reject_item(self):
        item = self._item()

        ItemBankService(event_publisher=Mock()).reject_item(item)

        self.assertEqual(item.review_status, ItemReviewStatus.REJECTED)
        item.save.assert_called_once()

    def test_mark_item_quality(self):
        item = self._item()

        ItemBankService(event_publisher=Mock()).mark_item_quality(item, ItemQualityStatus.HIGH)

        self.assertEqual(item.quality_status, ItemQualityStatus.HIGH)
        item.save.assert_called_once()

    def test_add_option(self):
        publisher = Mock()
        service = ItemBankService(event_publisher=publisher)
        item = self._item()

        with patch("apps.assessments.services.item_bank_service.ItemOption.objects") as option_objects:
            option_objects.filter.return_value.exists.return_value = False
            fake_option = self._option(item)
            option_objects.create.return_value = fake_option

            option = service.add_option(item, "A", "Option A", 1, is_correct=True)

        self.assertIs(option, fake_option)
        option_objects.create.assert_called_once_with(
            item_bank_entry=item,
            label="A",
            content="Option A",
            is_correct=True,
            explanation="",
            sequence_number=1,
            metadata={},
        )
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.item_option_added")

    def test_update_option(self):
        publisher = Mock()
        option = self._option(self._item())

        ItemBankService(event_publisher=publisher).update_option(option, label="B", content="Updated", is_correct=True)

        self.assertEqual(option.label, "B")
        self.assertEqual(option.content, "Updated")
        self.assertTrue(option.is_correct)
        option.save.assert_called_once()
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.item_option_updated")

    def test_remove_option(self):
        publisher = Mock()
        option = self._option(self._item())

        ItemBankService(event_publisher=publisher).remove_option(option)

        option.delete.assert_called_once()
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.item_option_removed")

    def test_option_sequence_uniqueness(self):
        service = ItemBankService(event_publisher=Mock())

        with patch("apps.assessments.services.item_bank_service.ItemOption.objects") as option_objects:
            option_objects.filter.return_value.exists.return_value = True

            with self.assertRaises(ValueError):
                service.add_option(self._item(), "A", "Duplicate", 1)

    def test_invalid_option_sequence_rejected(self):
        service = ItemBankService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.add_option(self._item(), "A", "Invalid", 0)

    def test_list_items_for_concept(self):
        service = ItemBankService(event_publisher=Mock())
        concept = DummyContentConcept()
        expected = [self._item()]

        with patch("apps.assessments.services.item_bank_service.ItemBankEntry.objects") as entry_objects:
            entry_objects.filter.return_value.order_by.return_value = expected
            items = service.list_items_for_concept(concept)

        self.assertEqual(items, expected)
        entry_objects.filter.assert_called_once_with(content_concept=concept)
        entry_objects.filter.return_value.order_by.assert_called_once_with("-created_at")

    def test_add_item_to_assessment(self):
        publisher = Mock()
        service = ItemBankService(event_publisher=publisher)
        assessment = self._assessment()
        item = self._item()

        with patch("apps.assessments.services.item_bank_service.AssessmentItemBankLink.objects") as link_objects:
            link_objects.filter.return_value.exists.return_value = False
            fake_link = self._link(assessment, item)
            link_objects.create.return_value = fake_link

            link = service.add_item_to_assessment(assessment, item, 1)

        self.assertIs(link, fake_link)
        link_objects.create.assert_called_once_with(
            assessment=assessment,
            item_bank_entry=item,
            sequence_number=1,
            metadata={},
        )
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.item_added_to_assessment")

    def test_remove_item_from_assessment(self):
        publisher = Mock()
        link = self._link(self._assessment(), self._item())

        ItemBankService(event_publisher=publisher).remove_item_from_assessment(link)

        link.delete.assert_called_once()
        self.assertEqual(publisher.publish.call_args.args[0].event_name, "assessment.item_removed_from_assessment")

    def test_list_items_for_assessment_ordered_by_sequence_number(self):
        service = ItemBankService(event_publisher=Mock())
        assessment = self._assessment()
        expected = [self._link(assessment, self._item())]

        with patch("apps.assessments.services.item_bank_service.AssessmentItemBankLink.objects") as link_objects:
            link_objects.filter.return_value.order_by.return_value = expected
            links = service.list_items_for_assessment(assessment)

        self.assertEqual(links, expected)
        link_objects.filter.assert_called_once_with(assessment=assessment)
        link_objects.filter.return_value.order_by.assert_called_once_with("sequence_number")

    def test_duplicate_item_cannot_be_added_to_same_assessment(self):
        service = ItemBankService(event_publisher=Mock())

        with patch("apps.assessments.services.item_bank_service.AssessmentItemBankLink.objects") as link_objects:
            link_objects.filter.return_value.exists.side_effect = [True]

            with self.assertRaises(ValueError):
                service.add_item_to_assessment(self._assessment(), self._item(), 1)

    def test_duplicate_sequence_cannot_be_used_in_same_assessment(self):
        service = ItemBankService(event_publisher=Mock())

        with patch("apps.assessments.services.item_bank_service.AssessmentItemBankLink.objects") as link_objects:
            link_objects.filter.return_value.exists.side_effect = [False, True]

            with self.assertRaises(ValueError):
                service.add_item_to_assessment(self._assessment(), self._item(), 1)

    def test_event_publishing_for_all_lifecycle_actions(self):
        publisher = Mock()
        service = ItemBankService(event_publisher=publisher)
        item = self._item()
        option = self._option(item)
        link = self._link(self._assessment(), item)

        with patch("apps.assessments.services.item_bank_service.ItemBankEntry.objects") as entry_objects:
            entry_objects.create.return_value = item
            service.create_item(DummyContentConcept(), AssessmentItemType.SHORT_ANSWER, "Prompt")
        service.update_item(item, prompt="Updated")
        service.archive_item(item)
        service.submit_item_for_review(item)
        service.approve_item(item)
        service.reject_item(item)
        service.mark_item_quality(item, ItemQualityStatus.ACCEPTABLE)
        with patch("apps.assessments.services.item_bank_service.ItemOption.objects") as option_objects:
            option_objects.filter.return_value.exists.return_value = False
            option_objects.create.return_value = option
            service.add_option(item, "A", "Option", 1)
        service.update_option(option, content="Updated option")
        service.remove_option(option)
        with patch("apps.assessments.services.item_bank_service.AssessmentItemBankLink.objects") as link_objects:
            link_objects.filter.return_value.exists.return_value = False
            link_objects.create.return_value = link
            service.add_item_to_assessment(link.assessment, item, 1)
        service.remove_item_from_assessment(link)

        event_names = [call.args[0].event_name for call in publisher.publish.call_args_list]

        self.assertEqual(
            event_names,
            [
                "assessment.item_bank_entry_created",
                "assessment.item_bank_entry_updated",
                "assessment.item_bank_entry_archived",
                "assessment.item_bank_entry_submitted_for_review",
                "assessment.item_bank_entry_approved",
                "assessment.item_bank_entry_rejected",
                "assessment.item_bank_entry_quality_marked",
                "assessment.item_option_added",
                "assessment.item_option_updated",
                "assessment.item_option_removed",
                "assessment.item_added_to_assessment",
                "assessment.item_removed_from_assessment",
            ],
        )

    def test_events_are_registered_for_discovery(self):
        expected = {
            "assessment.item_bank_entry_created",
            "assessment.item_bank_entry_updated",
            "assessment.item_bank_entry_archived",
            "assessment.item_bank_entry_submitted_for_review",
            "assessment.item_bank_entry_approved",
            "assessment.item_bank_entry_rejected",
            "assessment.item_bank_entry_quality_marked",
            "assessment.item_option_added",
            "assessment.item_option_updated",
            "assessment.item_option_removed",
            "assessment.item_added_to_assessment",
            "assessment.item_removed_from_assessment",
        }

        self.assertTrue(expected.issubset(set(default_event_registry._subscribers)))

    def test_model_constraints(self):
        option_constraints = {constraint.name: constraint for constraint in ItemOption._meta.constraints}
        link_constraints = {constraint.name: constraint for constraint in AssessmentItemBankLink._meta.constraints}

        self.assertIsInstance(option_constraints["unique_item_option_sequence"], models.UniqueConstraint)
        self.assertIn("item_option_sequence_gte_1", option_constraints)
        self.assertIsInstance(link_constraints["unique_assessment_bank_link_sequence"], models.UniqueConstraint)
        self.assertIsInstance(link_constraints["unique_assessment_bank_link_item"], models.UniqueConstraint)
        self.assertIn("assessment_bank_link_sequence_gte_1", link_constraints)
        self.assertEqual(ItemOption._meta.ordering, ["sequence_number"])
        self.assertEqual(AssessmentItemBankLink._meta.ordering, ["sequence_number"])

    def _assessment(self):
        assessment = Mock(spec=Assessment)
        assessment.id = "assessment-1"
        return assessment

    def _item(self):
        item = Mock(spec=ItemBankEntry)
        item.id = "item-1"
        item.content_concept_id = "concept-1"
        item.item_type = AssessmentItemType.MULTIPLE_CHOICE
        item.prompt = "Prompt"
        item.explanation = ""
        item.difficulty = ItemDifficulty.UNKNOWN
        item.review_status = ItemReviewStatus.DRAFT
        item.quality_status = ItemQualityStatus.UNKNOWN
        item.metadata = {}
        item.save = Mock()
        return item

    def _option(self, item):
        option = Mock(spec=ItemOption)
        option.id = "option-1"
        option.item_bank_entry = item
        option.item_bank_entry_id = item.id
        option.label = "A"
        option.content = "Option A"
        option.is_correct = False
        option.explanation = ""
        option.sequence_number = 1
        option.metadata = {}
        option.save = Mock()
        option.delete = Mock()
        return option

    def _link(self, assessment, item):
        link = Mock(spec=AssessmentItemBankLink)
        link.id = "link-1"
        link.assessment = assessment
        link.assessment_id = assessment.id
        link.item_bank_entry = item
        link.item_bank_entry_id = item.id
        link.sequence_number = 1
        link.metadata = {}
        link.delete = Mock()
        return link
