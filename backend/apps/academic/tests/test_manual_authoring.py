from contextlib import contextmanager
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.academic.domain.models import ContentConcept, ContentSection
from apps.academic.services.manual_authoring_service import ManualAuthoringService


class DummyLearningResource:
    id = "resource-1"


class ManualAuthoringServiceTests(SimpleTestCase):
    def test_manual_section_creation(self):
        publisher = Mock()
        service = ManualAuthoringService(event_publisher=publisher)
        learning_resource = DummyLearningResource()

        with patch("apps.academic.services.manual_authoring_service.ContentSection.objects") as section_objects:
            fake_section = self._section()
            section_objects.create.return_value = fake_section

            section = service.create_section(learning_resource, "Section 1", 1)

        self.assertIs(section, fake_section)
        self.assertEqual(section.title, "Section 1")
        self._assert_last_event(publisher, "academic.manual_section_created")

    def test_manual_section_update(self):
        publisher = Mock()
        service = ManualAuthoringService(event_publisher=publisher)
        section = self._section()

        updated_section = service.update_section(section, title="Updated Section")

        self.assertIs(updated_section, section)
        self.assertEqual(updated_section.title, "Updated Section")
        section.save.assert_called_once()
        self._assert_last_event(publisher, "academic.manual_section_updated")

    def test_manual_section_archive(self):
        publisher = Mock()
        service = ManualAuthoringService(event_publisher=publisher)
        section = self._section()
        section.is_active = True

        archived_section = service.archive_section(section)

        self.assertIs(archived_section, section)
        self.assertFalse(archived_section.is_active)
        section.save.assert_called_once()
        self._assert_last_event(publisher, "academic.manual_section_archived")

    def test_manual_section_reorder(self):
        publisher = Mock()
        service = ManualAuthoringService(event_publisher=publisher)
        section = self._section(sequence_number=1)

        with self._patch_section_reorder_conflict(None), patch(
            "apps.academic.services.manual_authoring_service.transaction.atomic"
        ):
            reordered_section = service.reorder_section(section, 2)

        self.assertIs(reordered_section, section)
        section.save.assert_called_once()
        self._assert_last_event(publisher, "academic.manual_section_reordered")

    def test_section_reorder_preserves_requested_sequence_number(self):
        service = ManualAuthoringService(event_publisher=Mock())
        section = self._section(sequence_number=1)

        with self._patch_section_reorder_conflict(None), patch(
            "apps.academic.services.manual_authoring_service.transaction.atomic"
        ):
            service.reorder_section(section, 3)

        self.assertEqual(section.sequence_number, 3)

    def test_manual_concept_creation(self):
        publisher = Mock()
        service = ManualAuthoringService(event_publisher=publisher)
        section = self._section()

        with patch("apps.academic.services.manual_authoring_service.ContentConcept.objects") as concept_objects:
            fake_concept = self._concept()
            concept_objects.create.return_value = fake_concept

            concept = service.create_concept(section, "Concept 1", 1)

        self.assertIs(concept, fake_concept)
        self.assertEqual(concept.title, "Concept 1")
        self._assert_last_event(publisher, "academic.manual_concept_created")

    def test_manual_concept_update(self):
        publisher = Mock()
        service = ManualAuthoringService(event_publisher=publisher)
        concept = self._concept()

        updated_concept = service.update_concept(concept, title="Updated Concept")

        self.assertIs(updated_concept, concept)
        self.assertEqual(updated_concept.title, "Updated Concept")
        concept.save.assert_called_once()
        self._assert_last_event(publisher, "academic.manual_concept_updated")

    def test_manual_concept_archive(self):
        publisher = Mock()
        service = ManualAuthoringService(event_publisher=publisher)
        concept = self._concept()
        concept.is_active = True

        archived_concept = service.archive_concept(concept)

        self.assertIs(archived_concept, concept)
        self.assertFalse(archived_concept.is_active)
        concept.save.assert_called_once()
        self._assert_last_event(publisher, "academic.manual_concept_archived")

    def test_manual_concept_reorder(self):
        publisher = Mock()
        service = ManualAuthoringService(event_publisher=publisher)
        concept = self._concept(sequence_number=1)

        with self._patch_concept_reorder_conflict(None), patch(
            "apps.academic.services.manual_authoring_service.transaction.atomic"
        ):
            reordered_concept = service.reorder_concept(concept, 2)

        self.assertIs(reordered_concept, concept)
        concept.save.assert_called_once()
        self._assert_last_event(publisher, "academic.manual_concept_reordered")

    def test_concept_reorder_preserves_requested_sequence_number(self):
        service = ManualAuthoringService(event_publisher=Mock())
        concept = self._concept(sequence_number=1)

        with self._patch_concept_reorder_conflict(None), patch(
            "apps.academic.services.manual_authoring_service.transaction.atomic"
        ):
            service.reorder_concept(concept, 3)

        self.assertEqual(concept.sequence_number, 3)

    def test_invalid_section_sequence_number_rejected(self):
        service = ManualAuthoringService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.create_section(DummyLearningResource(), "Invalid", 0)

    def test_invalid_concept_sequence_number_rejected(self):
        service = ManualAuthoringService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.create_concept(self._section(), "Invalid", 0)

    def test_event_publishing_for_section_create_update_archive_reorder(self):
        publisher = Mock()
        service = ManualAuthoringService(event_publisher=publisher)
        learning_resource = DummyLearningResource()
        section = self._section()

        with patch("apps.academic.services.manual_authoring_service.ContentSection.objects") as section_objects:
            section_objects.create.return_value = section
            service.create_section(learning_resource, "Section 1", 1)

        service.update_section(section, title="Section 2")
        service.archive_section(section)

        with self._patch_section_reorder_conflict(None), patch(
            "apps.academic.services.manual_authoring_service.transaction.atomic"
        ):
            service.reorder_section(section, 2)

        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            [
                "academic.manual_section_created",
                "academic.manual_section_updated",
                "academic.manual_section_archived",
                "academic.manual_section_reordered",
            ],
        )

    def test_event_publishing_for_concept_create_update_archive_reorder(self):
        publisher = Mock()
        service = ManualAuthoringService(event_publisher=publisher)
        section = self._section()
        concept = self._concept()

        with patch("apps.academic.services.manual_authoring_service.ContentConcept.objects") as concept_objects:
            concept_objects.create.return_value = concept
            service.create_concept(section, "Concept 1", 1)

        service.update_concept(concept, title="Concept 2")
        service.archive_concept(concept)

        with self._patch_concept_reorder_conflict(None), patch(
            "apps.academic.services.manual_authoring_service.transaction.atomic"
        ):
            service.reorder_concept(concept, 2)

        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            [
                "academic.manual_concept_created",
                "academic.manual_concept_updated",
                "academic.manual_concept_archived",
                "academic.manual_concept_reordered",
            ],
        )

    def _section(self, sequence_number=1):
        section = Mock(spec=ContentSection)
        section.id = "section-1"
        section.learning_resource_id = "resource-1"
        section.title = "Section 1"
        section.sequence_number = sequence_number
        section.is_active = True
        return section

    def _concept(self, sequence_number=1):
        concept = Mock(spec=ContentConcept)
        concept.id = "concept-1"
        concept.content_section_id = "section-1"
        concept.title = "Concept 1"
        concept.sequence_number = sequence_number
        concept.is_active = True
        return concept

    @contextmanager
    def _patch_section_reorder_conflict(self, conflict):
        with patch("apps.academic.services.manual_authoring_service.ContentSection.objects") as section_objects:
            section_objects.select_for_update.return_value.filter.return_value.exclude.return_value.first.return_value = (
                conflict
            )
            yield section_objects

    @contextmanager
    def _patch_concept_reorder_conflict(self, conflict):
        with patch("apps.academic.services.manual_authoring_service.ContentConcept.objects") as concept_objects:
            concept_objects.select_for_update.return_value.filter.return_value.exclude.return_value.first.return_value = (
                conflict
            )
            yield concept_objects

    def _assert_last_event(self, publisher, event_name):
        publisher.publish.assert_called()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, event_name)
