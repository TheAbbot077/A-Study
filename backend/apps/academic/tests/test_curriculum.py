from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import SimpleTestCase

from apps.academic.domain.models import Curriculum, CurriculumUnit, Subject
from apps.academic.services.curriculum_service import CurriculumService


class DummyInstitution:
    id = "institution-1"


class DummySubject:
    id = "subject-1"


class CurriculumServiceTests(SimpleTestCase):
    def test_create_curriculum_publishes_event(self):
        publisher = Mock()
        service = CurriculumService(event_publisher=publisher)
        institution = DummyInstitution()
        subject = DummySubject()

        with patch("apps.academic.services.curriculum_service.Curriculum.objects") as curriculum_objects:
            fake_curriculum = Mock(spec=Curriculum)
            fake_curriculum.id = "curriculum-1"
            fake_curriculum.subject_id = subject.id
            fake_curriculum.institution_id = institution.id
            fake_curriculum.name = "Core Mathematics"
            fake_curriculum.version = "1.0"
            curriculum_objects.create.return_value = fake_curriculum

            curriculum = service.create_curriculum(subject, "Core Mathematics", institution=institution)

        self.assertIs(curriculum, fake_curriculum)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.curriculum_created")

    def test_update_curriculum_publishes_event(self):
        publisher = Mock()
        service = CurriculumService(event_publisher=publisher)
        curriculum = Mock(spec=Curriculum)
        curriculum.id = "curriculum-1"
        curriculum.subject_id = "subject-1"
        curriculum.institution_id = "institution-1"
        curriculum.name = "Core Mathematics"
        curriculum.version = "1.0"

        updated_curriculum = service.update_curriculum(curriculum, name="Advanced Mathematics")

        self.assertIs(updated_curriculum, curriculum)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.curriculum_updated")

    def test_archive_curriculum_publishes_event(self):
        publisher = Mock()
        service = CurriculumService(event_publisher=publisher)
        curriculum = Mock(spec=Curriculum)
        curriculum.id = "curriculum-1"
        curriculum.subject_id = "subject-1"
        curriculum.institution_id = "institution-1"
        curriculum.is_active = True

        archived_curriculum = service.archive_curriculum(curriculum)

        self.assertIs(archived_curriculum, curriculum)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.curriculum_archived")

    def test_get_and_list_curricula(self):
        service = CurriculumService(event_publisher=Mock())
        subject = DummySubject()
        expected_curricula = [Mock()]

        with patch("apps.academic.services.curriculum_service.Curriculum.objects") as curriculum_objects:
            curriculum_objects.filter.return_value.order_by.return_value = expected_curricula
            curriculum_objects.get.return_value = expected_curricula[0]

            listed = service.list_curricula(subject)
            fetched = service.get_curriculum(subject, "curriculum-1")

        self.assertEqual(listed, expected_curricula)
        self.assertIs(fetched, expected_curricula[0])

    def test_create_unit_publishes_event(self):
        publisher = Mock()
        service = CurriculumService(event_publisher=publisher)
        curriculum = Mock(spec=Curriculum)
        curriculum.id = "curriculum-1"

        with patch("apps.academic.services.curriculum_service.CurriculumUnit.objects") as unit_objects:
            fake_unit = Mock(spec=CurriculumUnit)
            fake_unit.id = "unit-1"
            fake_unit.title = "Unit 1"
            fake_unit.sequence_number = 1
            unit_objects.create.return_value = fake_unit

            unit = service.create_unit(curriculum, "Unit 1", 1)

        self.assertIs(unit, fake_unit)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.curriculum_unit_created")

    def test_update_unit_publishes_event(self):
        publisher = Mock()
        service = CurriculumService(event_publisher=publisher)
        unit = Mock(spec=CurriculumUnit)
        unit.id = "unit-1"
        unit.curriculum_id = "curriculum-1"
        unit.title = "Unit 1"
        unit.sequence_number = 1

        updated_unit = service.update_unit(unit, title="Unit 2")

        self.assertIs(updated_unit, unit)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.curriculum_unit_updated")

    def test_archive_unit_publishes_event(self):
        publisher = Mock()
        service = CurriculumService(event_publisher=publisher)
        unit = Mock(spec=CurriculumUnit)
        unit.id = "unit-1"
        unit.curriculum_id = "curriculum-1"
        unit.sequence_number = 1
        unit.is_active = True

        archived_unit = service.archive_unit(unit)

        self.assertIs(archived_unit, unit)
        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "academic.curriculum_unit_archived")

    def test_list_units_orders_by_sequence_number(self):
        service = CurriculumService(event_publisher=Mock())
        curriculum = Mock(spec=Curriculum)
        expected_units = [Mock(), Mock()]

        with patch("apps.academic.services.curriculum_service.CurriculumUnit.objects") as unit_objects:
            unit_objects.filter.return_value.order_by.return_value = expected_units
            listed = service.list_units(curriculum)

        self.assertEqual(listed, expected_units)

    def test_curriculum_model_constraints(self):
        self.assertIn("subject", Curriculum._meta.get_field("subject").name)
        self.assertEqual(CurriculumUnit._meta.get_field("sequence_number").get_internal_type(), "PositiveIntegerField")
