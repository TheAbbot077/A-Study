from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.assessments.domain.models import (
    AssessmentBlueprint,
    AssessmentEvidenceRequirement,
    AssessmentItemType,
    AssessmentStrategy,
    AssessmentStrategyStep,
    AssessmentStrategyType,
    LearningEvidenceType,
    MasteryDecisionValue,
)
from apps.assessments.services import AssessmentStrategyService
from apps.core.events import default_event_registry


class AssessmentStrategyServiceTests(SimpleTestCase):
    def test_list_supported_strategies(self):
        strategies = AssessmentStrategyService(event_publisher=Mock()).list_supported_strategies()

        self.assertEqual(
            strategies,
            [
                "concept_check",
                "knowledge_recall",
                "worked_problem",
                "applied_reasoning",
                "calculation_practice",
                "reflective_explanation",
                "teach_back_preparation",
                "oral_probe",
                "mixed_evidence",
                "review_check",
            ],
        )

    def test_select_strategy_with_no_mastery_profile(self):
        strategy = AssessmentStrategyService(event_publisher=Mock()).select_strategy(self._concept())

        self.assertEqual(strategy.strategy_type, AssessmentStrategyType.CONCEPT_CHECK)

    def test_select_strategy_for_not_enough_evidence(self):
        strategy = AssessmentStrategyService(event_publisher=Mock()).select_strategy(
            self._concept(),
            mastery_profile=self._profile(MasteryDecisionValue.NOT_ENOUGH_EVIDENCE),
        )

        self.assertEqual(strategy.strategy_type, AssessmentStrategyType.CONCEPT_CHECK)

    def test_select_strategy_for_emerging_mastery(self):
        strategy = AssessmentStrategyService(event_publisher=Mock()).select_strategy(
            self._concept(),
            mastery_profile=self._profile(MasteryDecisionValue.EMERGING),
        )

        self.assertEqual(strategy.strategy_type, AssessmentStrategyType.WORKED_PROBLEM)

    def test_select_strategy_for_not_mastered(self):
        strategy = AssessmentStrategyService(event_publisher=Mock()).select_strategy(
            self._concept(),
            mastery_profile=self._profile(MasteryDecisionValue.NOT_MASTERED),
        )

        self.assertEqual(strategy.strategy_type, AssessmentStrategyType.REVIEW_CHECK)

    def test_select_strategy_for_needs_review(self):
        strategy = AssessmentStrategyService(event_publisher=Mock()).select_strategy(
            self._concept(),
            mastery_profile=self._profile(MasteryDecisionValue.NEEDS_REVIEW),
        )

        self.assertEqual(strategy.strategy_type, AssessmentStrategyType.MIXED_EVIDENCE)

    def test_select_strategy_for_mastered(self):
        strategy = AssessmentStrategyService(event_publisher=Mock()).select_strategy(
            self._concept(),
            mastery_profile=self._profile(MasteryDecisionValue.MASTERED),
        )

        self.assertEqual(strategy.strategy_type, AssessmentStrategyType.REVIEW_CHECK)

    def test_build_blueprint(self):
        blueprint = AssessmentStrategyService(event_publisher=Mock()).build_blueprint(
            self._concept(),
            mastery_profile=self._profile(MasteryDecisionValue.EMERGING),
        )

        self.assertEqual(blueprint.content_concept_id, "concept-1")
        self.assertEqual(blueprint.content_concept_title, "Opportunity Cost")
        self.assertEqual(blueprint.strategy.strategy_type, AssessmentStrategyType.WORKED_PROBLEM)
        self.assertEqual(blueprint.mastery_signal, MasteryDecisionValue.EMERGING)
        self.assertEqual(blueprint.recommended_item_count, 3)

    def test_blueprint_contains_recommended_item_types(self):
        blueprint = AssessmentStrategyService(event_publisher=Mock()).build_blueprint(
            self._concept(),
            strategy_type=AssessmentStrategyType.MIXED_EVIDENCE,
        )

        self.assertIn(AssessmentItemType.SHORT_ANSWER, blueprint.allowed_item_types)
        self.assertIn(AssessmentItemType.TEACH_BACK, blueprint.allowed_item_types)

    def test_blueprint_contains_evidence_requirements(self):
        blueprint = AssessmentStrategyService(event_publisher=Mock()).build_blueprint(
            self._concept(),
            strategy_type=AssessmentStrategyType.MIXED_EVIDENCE,
        )

        evidence_types = {requirement.evidence_type for requirement in blueprint.strategy.evidence_requirements}

        self.assertIn(LearningEvidenceType.CORRECT_RESPONSE, evidence_types)
        self.assertIn(LearningEvidenceType.EXPLANATION_QUALITY, evidence_types)

    def test_strategy_validation_success(self):
        service = AssessmentStrategyService(event_publisher=Mock())
        strategy = service.select_strategy(self._concept())

        self.assertEqual(service.validate_strategy(strategy), [])

    def test_strategy_validation_failure(self):
        service = AssessmentStrategyService(event_publisher=Mock())
        invalid_strategy = AssessmentStrategy(
            strategy_type="not_supported",
            name="",
            objective="",
            recommended_item_types=["not_an_item"],
            evidence_requirements=[
                AssessmentEvidenceRequirement(
                    evidence_type="not_evidence",
                    minimum_confidence=1.2,
                    required=True,
                )
            ],
            steps=[
                AssessmentStrategyStep(
                    sequence_number=2,
                    title="Out of Order",
                    goal="Expose invalid ordering.",
                    recommended_item_type="not_an_item",
                )
            ],
            estimated_difficulty="medium",
        )

        validation_errors = service.validate_strategy(invalid_strategy)

        self.assertIn("Assessment strategy must contain a supported strategy type.", validation_errors)
        self.assertIn("Assessment strategy must contain a name.", validation_errors)
        self.assertIn("Assessment strategy must contain an objective.", validation_errors)
        self.assertIn("Assessment strategy contains unsupported item type: not_an_item.", validation_errors)
        self.assertIn("Assessment strategy contains unsupported evidence type: not_evidence.", validation_errors)
        self.assertIn("Assessment evidence requirement confidence must be between 0 and 1.", validation_errors)
        self.assertIn("Assessment strategy steps must be ordered with contiguous sequence numbers starting at 1.", validation_errors)

    def test_blueprint_validation_success(self):
        service = AssessmentStrategyService(event_publisher=Mock())
        blueprint = service.build_blueprint(self._concept())

        self.assertEqual(service.validate_blueprint(blueprint), [])

    def test_blueprint_validation_failure(self):
        service = AssessmentStrategyService(event_publisher=Mock())
        valid_strategy = service.select_strategy(self._concept())
        invalid_blueprint = AssessmentBlueprint(
            content_concept_id="",
            content_concept_title="",
            strategy=valid_strategy,
            recommended_item_count=0,
            allowed_item_types=["not_an_item"],
            mastery_signal="",
        )

        validation_errors = service.validate_blueprint(invalid_blueprint)

        self.assertIn("Assessment blueprint must contain a content concept id.", validation_errors)
        self.assertIn("Assessment blueprint must contain a content concept title.", validation_errors)
        self.assertIn("Assessment blueprint recommended item count must be at least 1.", validation_errors)
        self.assertIn("Assessment blueprint contains unsupported item type: not_an_item.", validation_errors)
        self.assertIn("Assessment blueprint must contain a mastery signal.", validation_errors)

    def test_deterministic_behavior(self):
        service = AssessmentStrategyService(event_publisher=Mock())
        concept = self._concept()
        profile = self._profile(MasteryDecisionValue.NEEDS_REVIEW)

        first_blueprint = service.build_blueprint(concept, mastery_profile=profile)
        second_blueprint = service.build_blueprint(concept, mastery_profile=profile)

        self.assertEqual(first_blueprint, second_blueprint)

    def test_event_publishing(self):
        publisher = Mock()
        service = AssessmentStrategyService(event_publisher=publisher)
        blueprint = service.build_blueprint(self._concept())
        service.validate_strategy(blueprint.strategy)
        service.validate_blueprint(blueprint)

        event_names = [call.args[0].event_name for call in publisher.publish.call_args_list]

        self.assertIn("assessment.strategy_selected", event_names)
        self.assertIn("assessment.blueprint_built", event_names)
        self.assertIn("assessment.strategy_validated", event_names)
        self.assertIn("assessment.blueprint_validated", event_names)

    def test_strategy_events_are_registered_for_discovery(self):
        registered_event_names = set(default_event_registry._subscribers)

        self.assertIn("assessment.strategy_selected", registered_event_names)
        self.assertIn("assessment.blueprint_built", registered_event_names)
        self.assertIn("assessment.strategy_validated", registered_event_names)
        self.assertIn("assessment.blueprint_validated", registered_event_names)

    def test_academic_content_and_mastery_profile_remain_unchanged(self):
        concept = self._concept()
        profile = self._profile(MasteryDecisionValue.EMERGING)
        concept.save = Mock()
        profile.save = Mock()

        AssessmentStrategyService(event_publisher=Mock()).build_blueprint(concept, mastery_profile=profile)

        self.assertEqual(concept.title, "Opportunity Cost")
        self.assertEqual(profile.current_decision, MasteryDecisionValue.EMERGING)
        concept.save.assert_not_called()
        profile.save.assert_not_called()

    def _concept(self):
        return SimpleNamespace(
            id="concept-1",
            title="Opportunity Cost",
        )

    def _profile(self, current_decision):
        return SimpleNamespace(
            id="profile-1",
            current_decision=current_decision,
            confidence=0.7,
            evidence_count=2,
        )
