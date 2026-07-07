from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.academic.domain.models import ContentConcept, ContentSection, LearningResource
from apps.academic.services.learning_content_service import LearningContentService


class DummyLearningResource:
    id = "resource-1"


class LearningContentServiceTests(SimpleTestCase):
    def test_create_section_publishes_event(self):
        publisher = Mock()
        service = LearningContentService(event_publisher=publisher)
        learning_resource = DummyLearningResource()

        with patch("apps.academic.services.learning_content_service.ContentSection.objects") as section_objects:
            fake_section = Mock(spec=ContentSection)
            fake_section.id = "section-1"
            fake_section.title = "Section 1"
            fake_section.sequence_number = 1
            section_objects.create.return_value = fake_section

            section = service.create_section(learning_resource, "Section 1", 1)

        self.assertIs(section, fake_section)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.content_section_created")

    def test_update_section_publishes_event(self):
        publisher = Mock()
        service = LearningContentService(event_publisher=publisher)
        section = Mock(spec=ContentSection)
        section.id = "section-1"
        section.learning_resource_id = "resource-1"
        section.title = "Section 1"
        section.sequence_number = 1

        updated_section = service.update_section(section, title="Section 2")

        self.assertIs(updated_section, section)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.content_section_updated")

    def test_archive_section_publishes_event(self):
        publisher = Mock()
        service = LearningContentService(event_publisher=publisher)
        section = Mock(spec=ContentSection)
        section.id = "section-1"
        section.learning_resource_id = "resource-1"
        section.is_active = True

        archived_section = service.archive_section(section)

        self.assertIs(archived_section, section)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.content_section_archived")

    def test_get_and_list_sections(self):
        service = LearningContentService(event_publisher=Mock())
        learning_resource = DummyLearningResource()
        expected_sections = [Mock()]

        with patch("apps.academic.services.learning_content_service.ContentSection.objects") as section_objects:
            section_objects.filter.return_value.order_by.return_value = expected_sections
            section_objects.get.return_value = expected_sections[0]

            listed = service.list_sections(learning_resource)
            fetched = service.get_section(learning_resource, "section-1")

        self.assertEqual(listed, expected_sections)
        self.assertIs(fetched, expected_sections[0])

    def test_create_concept_publishes_event(self):
        publisher = Mock()
        service = LearningContentService(event_publisher=publisher)
        section = Mock(spec=ContentSection)
        section.id = "section-1"

        with patch("apps.academic.services.learning_content_service.ContentConcept.objects") as concept_objects:
            fake_concept = Mock(spec=ContentConcept)
            fake_concept.id = "concept-1"
            fake_concept.title = "Concept 1"
            fake_concept.sequence_number = 1
            concept_objects.create.return_value = fake_concept

            concept = service.create_concept(section, "Concept 1", 1)

        self.assertIs(concept, fake_concept)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.content_concept_created")

    def test_update_concept_publishes_event(self):
        publisher = Mock()
        service = LearningContentService(event_publisher=publisher)
        concept = Mock(spec=ContentConcept)
        concept.id = "concept-1"
        concept.content_section_id = "section-1"
        concept.title = "Concept 1"
        concept.sequence_number = 1

        updated_concept = service.update_concept(concept, title="Concept 2")

        self.assertIs(updated_concept, concept)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.content_concept_updated")

    def test_archive_concept_publishes_event(self):
        publisher = Mock()
        service = LearningContentService(event_publisher=publisher)
        concept = Mock(spec=ContentConcept)
        concept.id = "concept-1"
        concept.content_section_id = "section-1"
        concept.is_active = True

        archived_concept = service.archive_concept(concept)

        self.assertIs(archived_concept, concept)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.content_concept_archived")

    def test_get_and_list_concepts(self):
        service = LearningContentService(event_publisher=Mock())
        section = Mock(spec=ContentSection)
        expected_concepts = [Mock()]

        with patch("apps.academic.services.learning_content_service.ContentConcept.objects") as concept_objects:
            concept_objects.filter.return_value.order_by.return_value = expected_concepts
            concept_objects.get.return_value = expected_concepts[0]

            listed = service.list_concepts(section)
            fetched = service.get_concept(section, "concept-1")

        self.assertEqual(listed, expected_concepts)
        self.assertIs(fetched, expected_concepts[0])
