from __future__ import annotations

from typing import Any, Optional

from apps.academic.domain.models import ContentConcept
from apps.assessments.domain.models import (
    AssessmentBlueprint,
    AssessmentEvidenceRequirement,
    AssessmentItemType,
    AssessmentStrategy,
    AssessmentStrategyStep,
    AssessmentStrategyType,
    LearningEvidenceType,
    MasteryDecisionValue,
    MasteryProfile,
)
from apps.core.events import BusinessEvent, EventPublisher


class AssessmentStrategyService:
    STRATEGY_ORDER = [
        AssessmentStrategyType.CONCEPT_CHECK,
        AssessmentStrategyType.KNOWLEDGE_RECALL,
        AssessmentStrategyType.WORKED_PROBLEM,
        AssessmentStrategyType.APPLIED_REASONING,
        AssessmentStrategyType.CALCULATION_PRACTICE,
        AssessmentStrategyType.REFLECTIVE_EXPLANATION,
        AssessmentStrategyType.TEACH_BACK_PREPARATION,
        AssessmentStrategyType.ORAL_PROBE,
        AssessmentStrategyType.MIXED_EVIDENCE,
        AssessmentStrategyType.REVIEW_CHECK,
    ]

    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def select_strategy(
        self,
        content_concept: ContentConcept,
        mastery_profile: Optional[MasteryProfile] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AssessmentStrategy:
        strategy_type = self._select_strategy_type(mastery_profile)
        strategy = self._build_strategy(strategy_type, context=context)
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.strategy_selected",
                payload={
                    "content_concept_id": str(content_concept.id),
                    "strategy_type": strategy.strategy_type,
                    "mastery_signal": self._mastery_signal(mastery_profile),
                },
            )
        )
        return strategy

    def build_blueprint(
        self,
        content_concept: ContentConcept,
        strategy_type: Optional[str] = None,
        mastery_profile: Optional[MasteryProfile] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AssessmentBlueprint:
        strategy = (
            self._build_strategy(strategy_type, context=context)
            if strategy_type
            else self.select_strategy(content_concept, mastery_profile=mastery_profile, context=context)
        )
        blueprint = AssessmentBlueprint(
            content_concept_id=str(content_concept.id),
            content_concept_title=content_concept.title,
            strategy=strategy,
            recommended_item_count=self._recommended_item_count(strategy),
            allowed_item_types=list(strategy.recommended_item_types),
            mastery_signal=self._mastery_signal(mastery_profile),
            metadata={
                "source": "assessment_strategy_service",
                "context_keys": sorted((context or {}).keys()),
            },
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.blueprint_built",
                payload={
                    "content_concept_id": blueprint.content_concept_id,
                    "strategy_type": strategy.strategy_type,
                    "recommended_item_count": blueprint.recommended_item_count,
                    "mastery_signal": blueprint.mastery_signal,
                },
            )
        )
        return blueprint

    def validate_strategy(self, strategy: AssessmentStrategy) -> list[str]:
        validation_errors: list[str] = []

        if strategy.strategy_type not in AssessmentStrategyType.values:
            validation_errors.append("Assessment strategy must contain a supported strategy type.")
        if not strategy.name:
            validation_errors.append("Assessment strategy must contain a name.")
        if not strategy.objective:
            validation_errors.append("Assessment strategy must contain an objective.")
        if not strategy.recommended_item_types:
            validation_errors.append("Assessment strategy must contain recommended item types.")
        for item_type in strategy.recommended_item_types:
            if item_type not in AssessmentItemType.values:
                validation_errors.append(f"Assessment strategy contains unsupported item type: {item_type}.")
        if not strategy.evidence_requirements:
            validation_errors.append("Assessment strategy must contain evidence requirements.")
        for requirement in strategy.evidence_requirements:
            if requirement.evidence_type not in LearningEvidenceType.values:
                validation_errors.append(f"Assessment strategy contains unsupported evidence type: {requirement.evidence_type}.")
            if not 0.0 <= requirement.minimum_confidence <= 1.0:
                validation_errors.append("Assessment evidence requirement confidence must be between 0 and 1.")
        if not strategy.steps:
            validation_errors.append("Assessment strategy must contain ordered steps.")
        expected_sequence_numbers = list(range(1, len(strategy.steps) + 1))
        actual_sequence_numbers = [step.sequence_number for step in strategy.steps]
        if actual_sequence_numbers != expected_sequence_numbers:
            validation_errors.append("Assessment strategy steps must be ordered with contiguous sequence numbers starting at 1.")
        for step in strategy.steps:
            if step.recommended_item_type not in AssessmentItemType.values:
                validation_errors.append(f"Assessment strategy step contains unsupported item type: {step.recommended_item_type}.")

        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.strategy_validated",
                payload={
                    "strategy_type": strategy.strategy_type,
                    "is_valid": not validation_errors,
                    "validation_errors": validation_errors,
                },
            )
        )
        return validation_errors

    def validate_blueprint(self, blueprint: AssessmentBlueprint) -> list[str]:
        validation_errors: list[str] = []

        if not blueprint.content_concept_id:
            validation_errors.append("Assessment blueprint must contain a content concept id.")
        if not blueprint.content_concept_title:
            validation_errors.append("Assessment blueprint must contain a content concept title.")
        if blueprint.recommended_item_count < 1:
            validation_errors.append("Assessment blueprint recommended item count must be at least 1.")
        if not blueprint.allowed_item_types:
            validation_errors.append("Assessment blueprint must contain allowed item types.")
        for item_type in blueprint.allowed_item_types:
            if item_type not in AssessmentItemType.values:
                validation_errors.append(f"Assessment blueprint contains unsupported item type: {item_type}.")
        if not blueprint.mastery_signal:
            validation_errors.append("Assessment blueprint must contain a mastery signal.")
        validation_errors.extend(self.validate_strategy(blueprint.strategy))

        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.blueprint_validated",
                payload={
                    "content_concept_id": blueprint.content_concept_id,
                    "strategy_type": blueprint.strategy.strategy_type,
                    "is_valid": not validation_errors,
                    "validation_errors": validation_errors,
                },
            )
        )
        return validation_errors

    def list_supported_strategies(self) -> list[str]:
        return list(self.STRATEGY_ORDER)

    def _select_strategy_type(self, mastery_profile: Optional[MasteryProfile]) -> str:
        if mastery_profile is None:
            return AssessmentStrategyType.CONCEPT_CHECK

        decision = mastery_profile.current_decision
        if decision == MasteryDecisionValue.NOT_ENOUGH_EVIDENCE:
            return AssessmentStrategyType.CONCEPT_CHECK
        if decision == MasteryDecisionValue.EMERGING:
            return AssessmentStrategyType.WORKED_PROBLEM
        if decision == MasteryDecisionValue.NOT_MASTERED:
            return AssessmentStrategyType.REVIEW_CHECK
        if decision == MasteryDecisionValue.NEEDS_REVIEW:
            return AssessmentStrategyType.MIXED_EVIDENCE
        if decision == MasteryDecisionValue.MASTERED:
            return AssessmentStrategyType.REVIEW_CHECK
        return AssessmentStrategyType.CONCEPT_CHECK

    def _build_strategy(self, strategy_type: str, context: Optional[dict[str, Any]] = None) -> AssessmentStrategy:
        builders = {
            AssessmentStrategyType.CONCEPT_CHECK: self._concept_check,
            AssessmentStrategyType.KNOWLEDGE_RECALL: self._knowledge_recall,
            AssessmentStrategyType.WORKED_PROBLEM: self._worked_problem,
            AssessmentStrategyType.APPLIED_REASONING: self._applied_reasoning,
            AssessmentStrategyType.CALCULATION_PRACTICE: self._calculation_practice,
            AssessmentStrategyType.REFLECTIVE_EXPLANATION: self._reflective_explanation,
            AssessmentStrategyType.TEACH_BACK_PREPARATION: self._teach_back_preparation,
            AssessmentStrategyType.ORAL_PROBE: self._oral_probe,
            AssessmentStrategyType.MIXED_EVIDENCE: self._mixed_evidence,
            AssessmentStrategyType.REVIEW_CHECK: self._review_check,
        }
        if strategy_type not in builders:
            raise ValueError(f"Unsupported assessment strategy type: {strategy_type}.")
        return builders[strategy_type](context or {})

    def _strategy(
        self,
        strategy_type: str,
        name: str,
        objective: str,
        recommended_item_types: list[str],
        evidence_requirements: list[tuple[str, float, bool]],
        steps: list[tuple[str, str, str]],
        estimated_difficulty: str,
        context: dict[str, Any],
    ) -> AssessmentStrategy:
        return AssessmentStrategy(
            strategy_type=strategy_type,
            name=name,
            objective=objective,
            recommended_item_types=recommended_item_types,
            evidence_requirements=[
                AssessmentEvidenceRequirement(
                    evidence_type=evidence_type,
                    minimum_confidence=minimum_confidence,
                    required=required,
                )
                for evidence_type, minimum_confidence, required in evidence_requirements
            ],
            steps=[
                AssessmentStrategyStep(
                    sequence_number=index,
                    title=title,
                    goal=goal,
                    recommended_item_type=recommended_item_type,
                )
                for index, (title, goal, recommended_item_type) in enumerate(steps, start=1)
            ],
            estimated_difficulty=estimated_difficulty,
            metadata={"context_keys": sorted(context.keys())},
        )

    def _concept_check(self, context: dict[str, Any]) -> AssessmentStrategy:
        return self._strategy(
            AssessmentStrategyType.CONCEPT_CHECK,
            "Concept Check",
            "Collect initial evidence that the learner recognizes and can explain the concept.",
            [AssessmentItemType.MULTIPLE_CHOICE, AssessmentItemType.SHORT_ANSWER],
            [(LearningEvidenceType.CORRECT_RESPONSE, 0.6, True), (LearningEvidenceType.PARTIAL_UNDERSTANDING, 0.5, False)],
            [
                ("Check Recognition", "Confirm the learner can identify the concept.", AssessmentItemType.MULTIPLE_CHOICE),
                ("Check Explanation", "Ask for a brief explanation in the learner's own words.", AssessmentItemType.SHORT_ANSWER),
            ],
            "low",
            context,
        )

    def _knowledge_recall(self, context: dict[str, Any]) -> AssessmentStrategy:
        return self._strategy(
            AssessmentStrategyType.KNOWLEDGE_RECALL,
            "Knowledge Recall",
            "Collect evidence that the learner remembers key facts or definitions.",
            [AssessmentItemType.MULTIPLE_CHOICE, AssessmentItemType.TRUE_FALSE, AssessmentItemType.SHORT_ANSWER],
            [(LearningEvidenceType.CORRECT_RESPONSE, 0.65, True)],
            [
                ("Recall Definition", "Check recall of the central definition.", AssessmentItemType.SHORT_ANSWER),
                ("Confirm Boundaries", "Check whether the learner can distinguish accurate from inaccurate claims.", AssessmentItemType.TRUE_FALSE),
            ],
            "low",
            context,
        )

    def _worked_problem(self, context: dict[str, Any]) -> AssessmentStrategy:
        return self._strategy(
            AssessmentStrategyType.WORKED_PROBLEM,
            "Worked Problem",
            "Collect evidence that the learner can apply the concept through a structured problem.",
            [AssessmentItemType.SHORT_ANSWER, AssessmentItemType.CALCULATION],
            [(LearningEvidenceType.APPLIED_REASONING, 0.7, True), (LearningEvidenceType.CORRECT_RESPONSE, 0.7, False)],
            [
                ("Set Up Problem", "Ask the learner to identify what the problem requires.", AssessmentItemType.SHORT_ANSWER),
                ("Solve Step", "Ask the learner to complete the central step.", AssessmentItemType.CALCULATION),
                ("Explain Reasoning", "Ask the learner to justify the result.", AssessmentItemType.SHORT_ANSWER),
            ],
            "medium",
            context,
        )

    def _applied_reasoning(self, context: dict[str, Any]) -> AssessmentStrategy:
        return self._strategy(
            AssessmentStrategyType.APPLIED_REASONING,
            "Applied Reasoning",
            "Collect evidence that the learner can transfer the concept into a new situation.",
            [AssessmentItemType.SHORT_ANSWER, AssessmentItemType.ESSAY, AssessmentItemType.CLINICAL],
            [(LearningEvidenceType.APPLIED_REASONING, 0.7, True), (LearningEvidenceType.EXPLANATION_QUALITY, 0.6, False)],
            [
                ("Present Scenario", "Ask the learner to analyze a fresh scenario.", AssessmentItemType.SHORT_ANSWER),
                ("Justify Choice", "Ask the learner to defend the reasoning used.", AssessmentItemType.ESSAY),
            ],
            "medium",
            context,
        )

    def _calculation_practice(self, context: dict[str, Any]) -> AssessmentStrategy:
        return self._strategy(
            AssessmentStrategyType.CALCULATION_PRACTICE,
            "Calculation Practice",
            "Collect evidence that the learner can perform required calculation steps accurately.",
            [AssessmentItemType.CALCULATION],
            [(LearningEvidenceType.CORRECT_RESPONSE, 0.75, True), (LearningEvidenceType.APPLIED_REASONING, 0.65, False)],
            [
                ("Compute Result", "Ask for the calculated answer.", AssessmentItemType.CALCULATION),
                ("Check Method", "Ask for the calculation method.", AssessmentItemType.CALCULATION),
            ],
            "medium",
            context,
        )

    def _reflective_explanation(self, context: dict[str, Any]) -> AssessmentStrategy:
        return self._strategy(
            AssessmentStrategyType.REFLECTIVE_EXPLANATION,
            "Reflective Explanation",
            "Collect evidence of understanding through a reflective learner explanation.",
            [AssessmentItemType.ESSAY, AssessmentItemType.ORAL, AssessmentItemType.SHORT_ANSWER],
            [(LearningEvidenceType.EXPLANATION_QUALITY, 0.7, True), (LearningEvidenceType.PARTIAL_UNDERSTANDING, 0.5, False)],
            [
                ("Explain Meaning", "Ask for a learner-authored explanation.", AssessmentItemType.ESSAY),
                ("Name Uncertainty", "Ask the learner to identify remaining uncertainty.", AssessmentItemType.SHORT_ANSWER),
            ],
            "medium",
            context,
        )

    def _teach_back_preparation(self, context: dict[str, Any]) -> AssessmentStrategy:
        return self._strategy(
            AssessmentStrategyType.TEACH_BACK_PREPARATION,
            "Teach-Back Preparation",
            "Collect evidence that the learner is ready to explain the concept to someone else.",
            [AssessmentItemType.TEACH_BACK, AssessmentItemType.ORAL],
            [(LearningEvidenceType.EXPLANATION_QUALITY, 0.75, True), (LearningEvidenceType.APPLIED_REASONING, 0.65, False)],
            [
                ("Prepare Explanation", "Ask the learner to plan a teach-back explanation.", AssessmentItemType.TEACH_BACK),
                ("Deliver Explanation", "Ask the learner to explain the concept aloud or in teach-back form.", AssessmentItemType.ORAL),
            ],
            "high",
            context,
        )

    def _oral_probe(self, context: dict[str, Any]) -> AssessmentStrategy:
        return self._strategy(
            AssessmentStrategyType.ORAL_PROBE,
            "Oral Probe",
            "Collect verbal evidence through a short probing exchange.",
            [AssessmentItemType.ORAL],
            [(LearningEvidenceType.MANUAL_OBSERVATION, 0.6, True), (LearningEvidenceType.EXPLANATION_QUALITY, 0.6, False)],
            [
                ("Ask Probe", "Prompt the learner to answer verbally.", AssessmentItemType.ORAL),
                ("Follow Up", "Probe the reasoning behind the answer.", AssessmentItemType.ORAL),
            ],
            "medium",
            context,
        )

    def _mixed_evidence(self, context: dict[str, Any]) -> AssessmentStrategy:
        return self._strategy(
            AssessmentStrategyType.MIXED_EVIDENCE,
            "Mixed Evidence",
            "Collect multiple forms of evidence when prior signals conflict or need review.",
            [AssessmentItemType.SHORT_ANSWER, AssessmentItemType.ORAL, AssessmentItemType.TEACH_BACK, AssessmentItemType.CALCULATION],
            [(LearningEvidenceType.CORRECT_RESPONSE, 0.65, True), (LearningEvidenceType.EXPLANATION_QUALITY, 0.65, True), (LearningEvidenceType.MISCONCEPTION, 0.6, False)],
            [
                ("Check Answer", "Ask for a direct response.", AssessmentItemType.SHORT_ANSWER),
                ("Check Reasoning", "Ask the learner to explain the reasoning.", AssessmentItemType.ORAL),
                ("Check Transfer", "Ask for a brief teach-back or application.", AssessmentItemType.TEACH_BACK),
            ],
            "high",
            context,
        )

    def _review_check(self, context: dict[str, Any]) -> AssessmentStrategy:
        return self._strategy(
            AssessmentStrategyType.REVIEW_CHECK,
            "Review Check",
            "Collect lightweight evidence to confirm retention or revisit a weak concept.",
            [AssessmentItemType.MULTIPLE_CHOICE, AssessmentItemType.SHORT_ANSWER],
            [(LearningEvidenceType.CORRECT_RESPONSE, 0.7, True), (LearningEvidenceType.MISCONCEPTION, 0.6, False)],
            [
                ("Confirm Recall", "Check whether the learner still recognizes the concept.", AssessmentItemType.MULTIPLE_CHOICE),
                ("Confirm Explanation", "Ask for a short explanation to reveal misconceptions.", AssessmentItemType.SHORT_ANSWER),
            ],
            "low",
            context,
        )

    def _recommended_item_count(self, strategy: AssessmentStrategy) -> int:
        if strategy.estimated_difficulty == "high":
            return 4
        if strategy.estimated_difficulty == "medium":
            return 3
        return 2

    def _mastery_signal(self, mastery_profile: Optional[MasteryProfile]) -> str:
        if mastery_profile is None:
            return "unprofiled"
        return mastery_profile.current_decision
