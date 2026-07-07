from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.academic.domain.models import Subject
from apps.academic.services.academic_structure_service import AcademicStructureService


class DummyInstitution:
    id = "institution-1"


class AcademicStructureServiceTests(SimpleTestCase):
    def test_create_subject_publishes_event(self):
        publisher = Mock()
        service = AcademicStructureService(event_publisher=publisher)
        institution = DummyInstitution()

        with patch("apps.academic.services.academic_structure_service.Subject.objects") as subject_objects:
            fake_subject = Mock(spec=Subject)
            fake_subject.id = "subject-1"
            fake_subject.code = "MAT101"
            fake_subject.name = "Mathematics"
            fake_subject.is_active = True
            subject_objects.create.return_value = fake_subject

            subject = service.create_subject(institution, "MAT101", "Mathematics")

        self.assertIs(subject, fake_subject)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.subject_created")

    def test_update_subject_publishes_event(self):
        publisher = Mock()
        service = AcademicStructureService(event_publisher=publisher)
        subject = Mock(spec=Subject)
        subject.id = "subject-1"
        subject.institution = DummyInstitution()
        subject.code = "MAT101"
        subject.name = "Mathematics"

        with patch("apps.academic.services.academic_structure_service.Subject.objects") as subject_objects:
            subject_objects.filter.return_value.first.return_value = subject
            updated_subject = service.update_subject(subject, name="Advanced Mathematics")

        self.assertIs(updated_subject, subject)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.subject_updated")

    def test_archive_subject_publishes_event(self):
        publisher = Mock()
        service = AcademicStructureService(event_publisher=publisher)
        subject = Mock(spec=Subject)
        subject.id = "subject-1"
        subject.institution = DummyInstitution()
        subject.code = "MAT101"
        subject.name = "Mathematics"
        subject.is_active = True

        with patch("apps.academic.services.academic_structure_service.Subject.objects") as subject_objects:
            subject_objects.filter.return_value.first.return_value = subject
            archived_subject = service.archive_subject(subject)

        self.assertIs(archived_subject, subject)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.subject_archived")

    def test_list_and_get_subjects(self):
        service = AcademicStructureService(event_publisher=Mock())
        institution = DummyInstitution()
        expected_subjects = [Mock()]

        with patch("apps.academic.services.academic_structure_service.Subject.objects") as subject_objects:
            subject_objects.filter.return_value.order_by.return_value = expected_subjects
            subject_objects.get.return_value = expected_subjects[0]

            listed = service.list_subjects(institution)
            fetched = service.get_subject(institution, "subject-1")

        self.assertEqual(listed, expected_subjects)
        self.assertIs(fetched, expected_subjects[0])
