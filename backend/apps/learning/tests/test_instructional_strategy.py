from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.core.events import default_event_registry
from apps.learning.domain.models import InstructionalStrategy, StrategyStep
from apps.learning.services import ContextAssemblyService, GroundingService, InstructionalStrategyService


class InstructionalStrategyServiceTests(SimpleTestCase):
    def test_strategy_selection(self):
        recommendation = InstructionalStrategyService(event_publisher=Mock()).select_strategy(self._grounded_package())

        self.assertEqual(recommendation.strategy.strategy_identifier, InstructionalStrategyService.CONCEPT_MAPPING)
        self.assertEqual(recommendation.strategy.name, "Concept Mapping")
        self.assertIn(InstructionalStrategyService.DIRECT_INSTRUCTION, recommendation.considered_strategy_identifiers)

    def test_deterministic_strategy_selection(self):
        service = InstructionalStrategyService(event_publisher=Mock())
        package = self._grounded_package()

        first_recommendation = service.select_strategy(package)
        second_recommendation = service.select_strategy(package)

        self.assertEqual(first_recommendation.strategy, second_recommendation.strategy)
        self.assertEqual(first_recommendation.rationale, second_recommendation.rationale)

    def test_strategy_construction_for_all_builtin_strategies(self):
        service = InstructionalStrategyService(event_publisher=Mock())
        package = self._grounded_package()

        for strategy_identifier in InstructionalStrategyService.STRATEGY_ORDER:
            strategy = service.build_strategy(strategy_identifier, package)

            self.assertEqual(strategy.strategy_identifier, strategy_identifier)
            self.assertTrue(strategy.name)
            self.assertTrue(strategy.pedagogical_objective)
            self.assertTrue(strategy.ordered_instructional_steps)
            self.assertTrue(strategy.estimated_complexity)

    def test_ordered_strategy_steps(self):
        service = InstructionalStrategyService(event_publisher=Mock())
        strategy = service.build_strategy(InstructionalStrategyService.WORKED_EXAMPLE, self._grounded_package())

        steps = service.list_strategy_steps(strategy)

        self.assertEqual([step.sequence_number for step in steps], [1, 2, 3])

    def test_strategy_validation(self):
        service = InstructionalStrategyService(event_publisher=Mock())
        strategy = service.build_strategy(InstructionalStrategyService.GUIDED_PRACTICE, self._grounded_package())

        validation_errors = service.validate_strategy(strategy)

        self.assertEqual(validation_errors, [])

    def test_invalid_strategy_detection(self):
        service = InstructionalStrategyService(event_publisher=Mock())
        invalid_strategy = InstructionalStrategy(
            strategy_identifier="",
            name="",
            pedagogical_objective="",
            estimated_complexity="medium",
            ordered_instructional_steps=[
                StrategyStep(
                    sequence_number=2,
                    title="Out of Order",
                    instructional_goal="Expose invalid ordering.",
                    recommended_interaction="No interaction.",
                )
            ],
        )

        validation_errors = service.validate_strategy(invalid_strategy)

        self.assertEqual(
            validation_errors,
            [
                "Instructional strategy must contain a strategy identifier.",
                "Instructional strategy must contain a human-readable name.",
                "Instructional strategy must contain a pedagogical objective.",
                "Instructional strategy steps must be ordered with contiguous sequence numbers starting at 1.",
            ],
        )

    def test_event_publication(self):
        publisher = Mock()
        service = InstructionalStrategyService(event_publisher=publisher)

        recommendation = service.select_strategy(self._grounded_package())
        service.validate_strategy(recommendation.strategy)

        self.assertEqual(
            [call.args[0].event_name for call in publisher.publish.call_args_list],
            ["learning.strategy_selected", "learning.strategy_validated"],
        )
        self.assertEqual(publisher.publish.call_args_list[0].args[0].payload["strategy_identifier"], "concept_mapping")
        self.assertTrue(publisher.publish.call_args_list[1].args[0].payload["is_valid"])

    def test_strategy_events_are_registered_for_discovery(self):
        registered_event_names = set(default_event_registry._subscribers)

        self.assertIn("learning.strategy_selected", registered_event_names)
        self.assertIn("learning.strategy_validated", registered_event_names)

    def test_academic_content_remains_unchanged(self):
        learner = SimpleNamespace(id="learner-1")
        concept = self._academic_concept()
        section = concept.content_section
        resource = section.learning_resource
        concept.save = Mock()
        section.save = Mock()
        resource.save = Mock()

        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(learner, concept)
        package = GroundingService(event_publisher=Mock()).build_grounding_package(context)
        InstructionalStrategyService(event_publisher=Mock()).select_strategy(package)

        self.assertEqual(concept.title, "Opportunity Cost")
        self.assertEqual(section.title, "Economic Choices")
        self.assertEqual(resource.title, "Economics Guide")
        concept.save.assert_not_called()
        section.save.assert_not_called()
        resource.save.assert_not_called()

    def test_low_confidence_package_selects_direct_instruction(self):
        service = InstructionalStrategyService(event_publisher=Mock())
        package = replace(self._grounded_package(), grounding_confidence=0.5)

        recommendation = service.select_strategy(package)

        self.assertEqual(recommendation.strategy.strategy_identifier, InstructionalStrategyService.DIRECT_INSTRUCTION)

    def _grounded_package(self):
        context = ContextAssemblyService(event_publisher=Mock()).assemble_for_concept(
            SimpleNamespace(id="learner-1"),
            self._academic_concept(),
            session_id="session-1",
        )
        return GroundingService(event_publisher=Mock()).build_grounding_package(context)

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
