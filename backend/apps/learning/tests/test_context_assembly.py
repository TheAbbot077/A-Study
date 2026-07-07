from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.core.events import default_event_registry
from apps.learning.services import ContextAssemblyService


class ContextAssemblyServiceTests(SimpleTestCase):
    def test_assemble_context_for_session(self):
        publisher = Mock()
        service = ContextAssemblyService(event_publisher=publisher)
        learner = self._learner()
        concept = self._concept()
        session = SimpleNamespace(id="session-1", learner=learner, content_concept=concept)

        context = service.assemble_for_session(session)

        self.assertEqual(context.session_id, "session-1")
        self.assertEqual(context.learner.learner_id, "learner-1")
        self.assertEqual(context.concept.content_concept_id, "concept-1")

    def test_assemble_context_directly_for_learner_and_concept(self):
        service = ContextAssemblyService(event_publisher=Mock())

        context = service.assemble_for_concept(self._learner(), self._concept())

        self.assertIsNone(context.session_id)
        self.assertEqual(context.learner.learner_id, "learner-1")
        self.assertEqual(context.concept.content_concept_id, "concept-1")

    def test_includes_concept_details(self):
        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(self._learner(), self._concept())

        self.assertEqual(context.concept.content_concept_title, "Opportunity Cost")
        self.assertEqual(context.concept.content_concept_description, "The value of the next best alternative.")
        self.assertEqual(context.concept.content_concept_learning_objective, "Explain opportunity cost.")
        self.assertEqual(context.concept.review_status, "approved")
        self.assertEqual(context.concept.quality_status, "high")

    def test_includes_section_details(self):
        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(self._learner(), self._concept())

        section = context.concept.content_section
        self.assertEqual(section.content_section_id, "section-1")
        self.assertEqual(section.content_section_title, "Economic Choices")
        self.assertEqual(section.review_status, "approved")
        self.assertEqual(section.quality_status, "high")

    def test_includes_learning_resource_details(self):
        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(self._learner(), self._concept())

        resource = context.concept.content_section.learning_resource
        self.assertEqual(resource.learning_resource_id, "resource-1")
        self.assertEqual(resource.learning_resource_title, "Economics Guide")
        self.assertEqual(resource.resource_type, "guide")

    def test_includes_subject_details_when_reachable(self):
        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(self._learner(), self._concept())

        resource = context.concept.content_section.learning_resource
        self.assertEqual(resource.subject_id, "subject-1")
        self.assertEqual(resource.subject_name, "Economics")

    def test_includes_curriculum_details_when_reachable(self):
        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(self._learner(), self._concept())

        curriculum = context.concept.content_section.learning_resource.curriculum
        self.assertEqual(curriculum.curriculum_id, "curriculum-1")
        self.assertEqual(curriculum.curriculum_name, "Intro Economics")

    def test_includes_curriculum_unit_details_when_reachable(self):
        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(self._learner(), self._concept())

        curriculum = context.concept.content_section.learning_resource.curriculum
        self.assertEqual(curriculum.curriculum_unit_id, "unit-1")
        self.assertEqual(curriculum.curriculum_unit_title, "Scarcity")

    def test_gracefully_handles_null_curriculum(self):
        concept = self._concept(curriculum=None)

        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(self._learner(), concept)

        curriculum = context.concept.content_section.learning_resource.curriculum
        self.assertIsNone(curriculum.curriculum_id)
        self.assertIsNone(curriculum.curriculum_name)

    def test_gracefully_handles_null_curriculum_unit(self):
        concept = self._concept(curriculum_unit=None)

        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(self._learner(), concept)

        curriculum = context.concept.content_section.learning_resource.curriculum
        self.assertIsNone(curriculum.curriculum_unit_id)
        self.assertIsNone(curriculum.curriculum_unit_title)

    def test_does_not_mutate_academic_objects(self):
        learner = self._learner()
        concept = self._concept()
        section = concept.content_section
        resource = section.learning_resource
        concept.save = Mock()
        section.save = Mock()
        resource.save = Mock()

        ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(learner, concept)

        self.assertEqual(concept.title, "Opportunity Cost")
        self.assertEqual(section.title, "Economic Choices")
        self.assertEqual(resource.title, "Economics Guide")
        concept.save.assert_not_called()
        section.save.assert_not_called()
        resource.save.assert_not_called()

    def test_publishes_context_assembled_event(self):
        publisher = Mock()
        service = ContextAssemblyService(event_publisher=publisher)

        service.assemble_for_concept(self._learner(), self._concept())

        publisher.publish.assert_called_once()
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "learning.context_assembled")
        self.assertEqual(event.payload["learner_id"], "learner-1")
        self.assertEqual(event.payload["content_concept_id"], "concept-1")
        self.assertIsNone(event.payload["session_id"])

    def test_context_assembled_event_is_registered_for_discovery(self):
        self.assertIn("learning.context_assembled", set(default_event_registry._subscribers))

    def _learner(self):
        return SimpleNamespace(id="learner-1")

    def _concept(self, curriculum=Ellipsis, curriculum_unit=Ellipsis):
        subject = SimpleNamespace(id="subject-1", name="Economics")
        if curriculum is Ellipsis:
            curriculum = SimpleNamespace(id="curriculum-1", name="Intro Economics")
        if curriculum_unit is Ellipsis:
            curriculum_unit = SimpleNamespace(id="unit-1", title="Scarcity")

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
            review_status="approved",
            quality_status="high",
            learning_resource=resource,
        )
        return SimpleNamespace(
            id="concept-1",
            title="Opportunity Cost",
            description="The value of the next best alternative.",
            learning_objective="Explain opportunity cost.",
            review_status="approved",
            quality_status="high",
            content_section=section,
        )
