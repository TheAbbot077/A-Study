from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.academic.domain.models import Curriculum, CurriculumUnit, LearningResource, Subject
from apps.academic.services.learning_resource_service import LearningResourceService


class DummyInstitution:
    id = "institution-1"


class DummySubject:
    id = "subject-1"


class LearningResourceServiceTests(SimpleTestCase):
    def test_create_resource_publishes_event(self):
        publisher = Mock()
        service = LearningResourceService(event_publisher=publisher)
        subject = DummySubject()

        with patch("apps.academic.services.learning_resource_service.LearningResource.objects") as resource_objects:
            fake_resource = Mock(spec=LearningResource)
            fake_resource.id = "resource-1"
            fake_resource.title = "Guide"
            fake_resource.resource_type = LearningResource.ResourceType.GUIDE
            fake_resource.status = LearningResource.Status.DRAFT
            resource_objects.create.return_value = fake_resource

            resource = service.create_resource(subject, "Guide", resource_type=LearningResource.ResourceType.GUIDE)

        self.assertIs(resource, fake_resource)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.learning_resource_created")

    def test_update_resource_publishes_event(self):
        publisher = Mock()
        service = LearningResourceService(event_publisher=publisher)
        resource = Mock(spec=LearningResource)
        resource.id = "resource-1"
        resource.title = "Guide"
        resource.resource_type = LearningResource.ResourceType.GUIDE
        resource.status = LearningResource.Status.DRAFT

        updated_resource = service.update_resource(resource, title="Updated Guide")

        self.assertIs(updated_resource, resource)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.learning_resource_updated")

    def test_activate_and_archive_resource_publish_events(self):
        publisher = Mock()
        service = LearningResourceService(event_publisher=publisher)
        resource = Mock(spec=LearningResource)
        resource.id = "resource-1"
        resource.title = "Guide"
        resource.status = LearningResource.Status.DRAFT

        activated = service.activate_resource(resource)
        archived = service.archive_resource(resource)

        self.assertIs(activated, resource)
        self.assertIs(archived, resource)
        self.assertEqual(publisher.publish.call_count, 2)

    def test_get_and_list_resources(self):
        service = LearningResourceService(event_publisher=Mock())
        subject = DummySubject()
        expected_resources = [Mock()]
        queryset = Mock()
        queryset.filter.return_value = queryset
        queryset.order_by.return_value = expected_resources

        with patch("apps.academic.services.learning_resource_service.LearningResource.objects") as resource_objects:
            resource_objects.all.return_value = queryset
            resource_objects.get.return_value = expected_resources[0]

            listed = service.list_resources(subject=subject)
            fetched = service.get_resource(subject, "resource-1")

        self.assertEqual(listed, expected_resources)
        self.assertIs(fetched, expected_resources[0])

    def test_allowed_resource_type_and_status_values(self):
        self.assertEqual(LearningResource.ResourceType.values, ["textbook", "notes", "guide", "reference", "other"])
        self.assertEqual(LearningResource.Status.values, ["draft", "active", "archived"])

    def test_optional_stored_file_is_supported(self):
        field = LearningResource._meta.get_field("stored_file")
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
