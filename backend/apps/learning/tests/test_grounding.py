from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.core.events import default_event_registry
from apps.learning.domain.models import GroundedTeachingPackage
from apps.learning.services import ContextAssemblyService, GroundingService


class GroundingServiceTests(SimpleTestCase):
    def test_grounding_package_creation(self):
        context = self._context()
        package = GroundingService(event_publisher=Mock()).build_grounding_package(context)

        self.assertIs(package.pedagogical_context, context)
        self.assertEqual(package.primary_concept.content_concept_id, "concept-1")
        self.assertEqual(package.review_status, "approved")
        self.assertEqual(package.quality_status, "high")
        self.assertEqual(package.grounding_confidence, 1.0)

    def test_primary_evidence_selection(self):
        package = GroundingService(event_publisher=Mock()).build_grounding_package(self._context())

        primary = package.primary_instructional_evidence
        self.assertEqual(primary.title, "Opportunity Cost")
        self.assertEqual(primary.description, "The value of the next best alternative.")
        self.assertEqual(primary.learning_objective, "Explain opportunity cost.")
        self.assertEqual(primary.source_reference.academic_object_type, "content_concept")
        self.assertEqual(primary.source_reference.relationship, "primary_concept")
        self.assertEqual(primary.source_reference.sequence_number, 2)

    def test_supporting_evidence_collection(self):
        package = GroundingService(event_publisher=Mock()).build_grounding_package(self._context())

        self.assertEqual(
            [evidence.evidence_type for evidence in package.supporting_evidence],
            ["parent_section", "source_resource", "curriculum", "curriculum_unit", "subject"],
        )

    def test_source_references_included(self):
        service = GroundingService(event_publisher=Mock())
        package = service.build_grounding_package(self._context())

        references = service.list_source_references(package)

        self.assertEqual(
            [(reference.academic_object_type, reference.object_id, reference.relationship) for reference in references],
            [
                ("content_concept", "concept-1", "primary_concept"),
                ("content_section", "section-1", "parent_section"),
                ("learning_resource", "resource-1", "source_resource"),
                ("curriculum", "curriculum-1", "curriculum"),
                ("curriculum_unit", "unit-1", "curriculum_unit"),
                ("subject", "subject-1", "subject"),
            ],
        )

    def test_deterministic_output(self):
        service = GroundingService(event_publisher=Mock())
        context = self._context()

        first_package = service.build_grounding_package(context)
        second_package = service.build_grounding_package(context)

        self.assertEqual(first_package.primary_instructional_evidence, second_package.primary_instructional_evidence)
        self.assertEqual(first_package.supporting_evidence, second_package.supporting_evidence)
        self.assertEqual(first_package.source_references, second_package.source_references)

    def test_validation_success(self):
        service = GroundingService(event_publisher=Mock())
        package = service.build_grounding_package(self._context())

        validation_errors = service.validate_grounding(package)

        self.assertEqual(validation_errors, [])

    def test_validation_failure_reports_errors(self):
        service = GroundingService(event_publisher=Mock())
        context = self._context()
        invalid_package = GroundedTeachingPackage(
            pedagogical_context=context,
            primary_concept=None,
            primary_instructional_evidence=None,
            source_references=[],
        )

        validation_errors = service.validate_grounding(invalid_package)

        self.assertEqual(
            validation_errors,
            [
                "Grounded teaching package must contain a primary concept.",
                "Grounded teaching package must contain primary evidence.",
                "Grounded teaching package must preserve source references.",
            ],
        )

    def test_grounding_events(self):
        publisher = Mock()
        service = GroundingService(event_publisher=publisher)

        package = service.build_grounding_package(self._context())
        service.validate_grounding(package)

        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            ["learning.grounding_package_created", "learning.grounding_validated"],
        )
        validation_event = publisher.publish.call_args_list[1].args[0]
        self.assertTrue(validation_event.payload["is_valid"])

    def test_grounding_events_are_registered_for_discovery(self):
        registered_event_names = set(default_event_registry._subscribers)

        self.assertIn("learning.grounding_package_created", registered_event_names)
        self.assertIn("learning.grounding_validated", registered_event_names)

    def test_academic_content_remains_unchanged(self):
        learner = SimpleNamespace(id="learner-1")
        concept = self._academic_concept()
        section = concept.content_section
        resource = section.learning_resource
        concept.save = Mock()
        section.save = Mock()
        resource.save = Mock()

        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(learner, concept)
        GroundingService(event_publisher=Mock()).build_grounding_package(context)

        self.assertEqual(concept.title, "Opportunity Cost")
        self.assertEqual(section.title, "Economic Choices")
        self.assertEqual(resource.title, "Economics Guide")
        concept.save.assert_not_called()
        section.save.assert_not_called()
        resource.save.assert_not_called()

    def _context(self):
        return ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(
            SimpleNamespace(id="learner-1"),
            self._academic_concept(),
            session_id="session-1",
        )

    def _academic_concept(self):
        subject = SimpleNamespace(id="subject-1", name="Economics")
        curriculum = SimpleNamespace(id="curriculum-1", name="Intro Economics")
        curriculum_unit = SimpleNamespace(id="unit-1", title="Scarcity", sequence_number=1)
        resource = SimpleNamespace(
            id="resource-1",
            title="Economics Guide",
            resource_type="guide",
            subject=subject,
            curriculum=curriculum,
            curriculum_unit=curriculum_unit,
        )
        section = SimpleNamespace(
            id="section-1",
            title="Economic Choices",
            sequence_number=1,
            review_status="approved",
            quality_status="high",
            learning_resource=resource,
        )
        return SimpleNamespace(
            id="concept-1",
            title="Opportunity Cost",
            description="The value of the next best alternative.",
            learning_objective="Explain opportunity cost.",
            sequence_number=2,
            review_status="approved",
            quality_status="high",
            content_section=section,
        )
