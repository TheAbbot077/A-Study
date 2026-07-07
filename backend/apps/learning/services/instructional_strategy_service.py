from __future__ import annotations

from typing import Optional

from apps.core.events import BusinessEvent, EventPublisher
from apps.learning.domain.models import GroundedTeachingPackage, InstructionalStrategy, StrategyRecommendation, StrategyStep


class InstructionalStrategyService:
    DIRECT_INSTRUCTION = "direct_instruction"
    WORKED_EXAMPLE = "worked_example"
    GUIDED_PRACTICE = "guided_practice"
    SOCRATIC_DIALOGUE = "socratic_dialogue"
    ANALOGY = "analogy"
    VISUAL_EXPLANATION = "visual_explanation"
    CONCEPT_MAPPING = "concept_mapping"
    PROBLEM_BASED_LEARNING = "problem_based_learning"

    STRATEGY_ORDER = [
        DIRECT_INSTRUCTION,
        WORKED_EXAMPLE,
        GUIDED_PRACTICE,
        SOCRATIC_DIALOGUE,
        ANALOGY,
        VISUAL_EXPLANATION,
        CONCEPT_MAPPING,
        PROBLEM_BASED_LEARNING,
    ]

    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def select_strategy(self, grounded_teaching_package: GroundedTeachingPackage) -> StrategyRecommendation:
        strategy_identifier, rationale = self._select_strategy_identifier(grounded_teaching_package)
        strategy = self.build_strategy(strategy_identifier, grounded_teaching_package)
        recommendation = StrategyRecommendation(
            grounded_teaching_package=grounded_teaching_package,
            strategy=strategy,
            rationale=rationale,
            considered_strategy_identifiers=list(self.STRATEGY_ORDER),
            metadata={"source": "instructional_strategy_service"},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.strategy_selected",
                payload={
                    "session_id": grounded_teaching_package.pedagogical_context.session_id,
                    "learner_id": grounded_teaching_package.pedagogical_context.learner.learner_id,
                    "content_concept_id": grounded_teaching_package.primary_concept.content_concept_id,
                    "strategy_identifier": strategy.strategy_identifier,
                },
            )
        )
        return recommendation

    def build_strategy(
        self,
        strategy_type: str,
        grounded_teaching_package: GroundedTeachingPackage,
    ) -> InstructionalStrategy:
        builders = {
            self.DIRECT_INSTRUCTION: self._build_direct_instruction,
            self.WORKED_EXAMPLE: self._build_worked_example,
            self.GUIDED_PRACTICE: self._build_guided_practice,
            self.SOCRATIC_DIALOGUE: self._build_socratic_dialogue,
            self.ANALOGY: self._build_analogy,
            self.VISUAL_EXPLANATION: self._build_visual_explanation,
            self.CONCEPT_MAPPING: self._build_concept_mapping,
            self.PROBLEM_BASED_LEARNING: self._build_problem_based_learning,
        }
        if strategy_type not in builders:
            raise ValueError(f"Unknown instructional strategy type: {strategy_type}.")
        return builders[strategy_type](grounded_teaching_package)

    def validate_strategy(self, strategy: InstructionalStrategy) -> list[str]:
        validation_errors: list[str] = []

        if not strategy.strategy_identifier:
            validation_errors.append("Instructional strategy must contain a strategy identifier.")
        if not strategy.name:
            validation_errors.append("Instructional strategy must contain a human-readable name.")
        if not strategy.pedagogical_objective:
            validation_errors.append("Instructional strategy must contain a pedagogical objective.")
        if not strategy.ordered_instructional_steps:
            validation_errors.append("Instructional strategy must contain ordered instructional steps.")
        expected_sequence_numbers = list(range(1, len(strategy.ordered_instructional_steps) + 1))
        actual_sequence_numbers = [step.sequence_number for step in strategy.ordered_instructional_steps]
        if actual_sequence_numbers != expected_sequence_numbers:
            validation_errors.append("Instructional strategy steps must be ordered with contiguous sequence numbers starting at 1.")

        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.strategy_validated",
                payload={
                    "strategy_identifier": strategy.strategy_identifier,
                    "is_valid": not validation_errors,
                    "validation_errors": validation_errors,
                },
            )
        )
        return validation_errors

    def list_strategy_steps(self, strategy: InstructionalStrategy) -> list[StrategyStep]:
        return sorted(strategy.ordered_instructional_steps, key=lambda step: step.sequence_number)

    def _select_strategy_identifier(self, package: GroundedTeachingPackage) -> tuple[str, str]:
        evidence_types = {evidence.evidence_type for evidence in package.supporting_evidence}

        if package.grounding_confidence < 0.75:
            return self.DIRECT_INSTRUCTION, "Low grounding confidence requires a tightly structured explanation."
        if "curriculum_unit" in evidence_types and "subject" in evidence_types:
            return self.CONCEPT_MAPPING, "Rich parent academic structure supports mapping the concept to its surrounding curriculum."
        if package.quality_status == "high":
            return self.WORKED_EXAMPLE, "High-quality primary evidence supports demonstrating the concept through an example."
        if package.primary_instructional_evidence and package.primary_instructional_evidence.learning_objective:
            return self.GUIDED_PRACTICE, "A clear learning objective supports learner practice with guidance."
        return self.DIRECT_INSTRUCTION, "Defaulting to explicit explanation for a stable first teaching pass."

    def _build_direct_instruction(self, package: GroundedTeachingPackage) -> InstructionalStrategy:
        return self._strategy(
            self.DIRECT_INSTRUCTION,
            "Direct Instruction",
            "Explain the concept clearly before inviting learner interaction.",
            "low",
            [
                ("State the Concept", "Name the target concept and its purpose.", "Explain using the primary evidence."),
                ("Define Key Meaning", "Clarify the core definition and boundaries.", "Present a concise explanation."),
                ("Check Readiness", "Confirm the learner can restate the idea.", "Ask for a brief learner response."),
            ],
            package,
        )

    def _build_worked_example(self, package: GroundedTeachingPackage) -> InstructionalStrategy:
        return self._strategy(
            self.WORKED_EXAMPLE,
            "Worked Example",
            "Demonstrate the concept through a structured example before learner practice.",
            "medium",
            [
                ("Introduce Example", "Connect the example to the primary concept.", "Present a simple grounded scenario."),
                ("Work Through Steps", "Show the reasoning process in sequence.", "Explain each step explicitly."),
                ("Invite Transfer", "Prepare the learner to apply the same reasoning.", "Ask what would change in a similar case."),
            ],
            package,
        )

    def _build_guided_practice(self, package: GroundedTeachingPackage) -> InstructionalStrategy:
        return self._strategy(
            self.GUIDED_PRACTICE,
            "Guided Practice",
            "Help the learner apply the concept with scaffolded support.",
            "medium",
            [
                ("Set Practice Goal", "Make the learning objective active.", "Frame a small task."),
                ("Prompt Attempt", "Encourage learner participation.", "Ask the learner to try one step."),
                ("Guide Correction", "Support refinement without taking over.", "Give targeted feedback."),
            ],
            package,
        )

    def _build_socratic_dialogue(self, package: GroundedTeachingPackage) -> InstructionalStrategy:
        return self._strategy(
            self.SOCRATIC_DIALOGUE,
            "Socratic Dialogue",
            "Use questions to help the learner uncover the concept.",
            "medium",
            [
                ("Elicit Prior Thinking", "Surface the learner's current model.", "Ask an open diagnostic question."),
                ("Probe Reasoning", "Reveal assumptions and misconceptions.", "Ask a follow-up why/how question."),
                ("Synthesize Insight", "Connect learner reasoning to the grounded concept.", "Summarize and invite confirmation."),
            ],
            package,
        )

    def _build_analogy(self, package: GroundedTeachingPackage) -> InstructionalStrategy:
        return self._strategy(
            self.ANALOGY,
            "Analogy",
            "Relate the concept to a familiar structure while preserving academic boundaries.",
            "medium",
            [
                ("Choose Familiar Frame", "Introduce an accessible comparison.", "Present a bounded analogy."),
                ("Map Similarities", "Connect analogy parts to the concept.", "Explain the useful parallels."),
                ("Name Limits", "Prevent overextension of the analogy.", "Clarify where the analogy stops applying."),
            ],
            package,
        )

    def _build_visual_explanation(self, package: GroundedTeachingPackage) -> InstructionalStrategy:
        return self._strategy(
            self.VISUAL_EXPLANATION,
            "Visual Explanation",
            "Represent the concept spatially or structurally before verbal elaboration.",
            "medium",
            [
                ("Identify Visual Structure", "Choose the simplest visual relationship.", "Describe the visual layout."),
                ("Walk the Diagram", "Explain each visual part in order.", "Narrate the relationship between parts."),
                ("Verify Interpretation", "Ensure the learner reads the visual correctly.", "Ask the learner to describe the structure."),
            ],
            package,
        )

    def _build_concept_mapping(self, package: GroundedTeachingPackage) -> InstructionalStrategy:
        return self._strategy(
            self.CONCEPT_MAPPING,
            "Concept Mapping",
            "Locate the concept within its section, resource, subject, and curriculum relationships.",
            "medium",
            [
                ("Anchor Concept", "Identify the primary concept.", "State the concept and its learning objective."),
                ("Map Parent Context", "Connect concept to section and resource.", "Describe the parent academic structure."),
                ("Connect Curriculum", "Show how the concept fits the curriculum path.", "Explain reachable curriculum and subject links."),
            ],
            package,
        )

    def _build_problem_based_learning(self, package: GroundedTeachingPackage) -> InstructionalStrategy:
        return self._strategy(
            self.PROBLEM_BASED_LEARNING,
            "Problem-Based Learning",
            "Introduce the concept through a problem that motivates understanding.",
            "high",
            [
                ("Present Problem", "Create a need for the concept.", "Pose a grounded problem scenario."),
                ("Explore Approaches", "Let the learner reason before explanation.", "Ask how they might begin."),
                ("Formalize Concept", "Tie the problem solution back to the source evidence.", "Explain the concept as the solution tool."),
            ],
            package,
        )

    def _strategy(
        self,
        strategy_identifier: str,
        name: str,
        pedagogical_objective: str,
        estimated_complexity: str,
        steps: list[tuple[str, str, str]],
        package: GroundedTeachingPackage,
    ) -> InstructionalStrategy:
        return InstructionalStrategy(
            strategy_identifier=strategy_identifier,
            name=name,
            pedagogical_objective=pedagogical_objective,
            ordered_instructional_steps=[
                StrategyStep(
                    sequence_number=index,
                    title=title,
                    instructional_goal=instructional_goal,
                    recommended_interaction=recommended_interaction,
                )
                for index, (title, instructional_goal, recommended_interaction) in enumerate(steps, start=1)
            ],
            estimated_complexity=estimated_complexity,
            metadata={
                "content_concept_id": package.primary_concept.content_concept_id,
                "grounding_confidence": package.grounding_confidence,
            },
        )
