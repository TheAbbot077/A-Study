from __future__ import annotations

from typing import Optional

from apps.core.events import BusinessEvent, EventPublisher
from apps.learning.domain.models import (
    AbbotGenerationPlan,
    AbbotResponseSection,
    AbbotTeachingRequest,
    AbbotTeachingResponse,
    GroundedTeachingPackage,
    InstructionalStrategy,
    PedagogicalMessage,
    PedagogicalSession,
    SourceReference,
)
from apps.learning.services.context_assembly_service import ContextAssemblyService
from apps.learning.services.conversation_orchestrator_service import ConversationOrchestratorService
from apps.learning.services.grounding_service import GroundingService
from apps.learning.services.instructional_strategy_service import InstructionalStrategyService


class AbbotResponseType:
    TEACHING = "teaching"
    CLARIFICATION = "clarification"
    SUMMARY = "summary"
    SYSTEM = "system"

    VALUES = {TEACHING, CLARIFICATION, SUMMARY, SYSTEM}


class AbbotTeachingAgentService:
    def __init__(
        self,
        event_publisher: Optional[EventPublisher] = None,
        context_assembly_service: Optional[ContextAssemblyService] = None,
        grounding_service: Optional[GroundingService] = None,
        strategy_service: Optional[InstructionalStrategyService] = None,
        conversation_orchestrator: Optional[ConversationOrchestratorService] = None,
    ) -> None:
        self.event_publisher = event_publisher or EventPublisher()
        self.context_assembly_service = context_assembly_service or ContextAssemblyService()
        self.grounding_service = grounding_service or GroundingService()
        self.strategy_service = strategy_service or InstructionalStrategyService()
        self.conversation_orchestrator = conversation_orchestrator or ConversationOrchestratorService()

    def prepare_teaching_request(self, session: PedagogicalSession) -> AbbotTeachingRequest:
        pedagogical_context = self.context_assembly_service.assemble_for_session(session)
        grounded_teaching_package = self.grounding_service.build_grounding_package(pedagogical_context)
        strategy_recommendation = self.strategy_service.select_strategy(grounded_teaching_package)
        conversation_context = self.conversation_orchestrator.build_conversation_context(session)
        generation_plan = AbbotGenerationPlan(
            response_type=AbbotResponseType.TEACHING,
            grounded_teaching_package=grounded_teaching_package,
            instructional_strategy=strategy_recommendation.strategy,
            conversation_context=conversation_context,
            metadata={"generator": "deterministic_placeholder"},
        )
        request = AbbotTeachingRequest(
            session=session,
            pedagogical_context=pedagogical_context,
            grounded_teaching_package=grounded_teaching_package,
            instructional_strategy=strategy_recommendation.strategy,
            conversation_context=conversation_context,
            generation_plan=generation_plan,
            metadata={"source": "abbot_teaching_agent_service"},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.abbot_request_prepared",
                payload={
                    "session_id": str(session.id),
                    "content_concept_id": grounded_teaching_package.primary_concept.content_concept_id,
                    "strategy_identifier": strategy_recommendation.strategy.strategy_identifier,
                },
            )
        )
        return request

    def generate_teaching_response(self, session: PedagogicalSession) -> AbbotTeachingResponse:
        request = self.prepare_teaching_request(session)
        response = self._generate_response(request, AbbotResponseType.TEACHING)
        self._add_abbot_message(session, response, PedagogicalMessage.MessageType.EXPLANATION)
        self._publish_response_generated(response)
        return response

    def generate_clarification_response(
        self,
        session: PedagogicalSession,
        learner_question: str,
    ) -> AbbotTeachingResponse:
        request = self.prepare_teaching_request(session)
        response = self._generate_response(
            request,
            AbbotResponseType.CLARIFICATION,
            metadata={"learner_question": learner_question},
        )
        self._add_abbot_message(session, response, PedagogicalMessage.MessageType.CLARIFICATION)
        self._publish_response_generated(response)
        return response

    def generate_summary_response(self, session: PedagogicalSession) -> AbbotTeachingResponse:
        request = self.prepare_teaching_request(session)
        response = self._generate_response(request, AbbotResponseType.SUMMARY)
        self._add_abbot_message(session, response, PedagogicalMessage.MessageType.SUMMARY)
        self._publish_response_generated(response)
        return response

    def validate_response(self, response: AbbotTeachingResponse) -> list[str]:
        validation_errors: list[str] = []
        if response.response_type not in AbbotResponseType.VALUES:
            validation_errors.append("Abbot teaching response must use a supported response type.")
        if not response.session_id:
            validation_errors.append("Abbot teaching response must include a session id.")
        if not response.concept_title:
            validation_errors.append("Abbot teaching response must include a concept title.")
        if not response.sections:
            validation_errors.append("Abbot teaching response must include response sections.")
        if not response.source_references:
            validation_errors.append("Abbot teaching response must include source references.")
        if not response.strategy_used:
            validation_errors.append("Abbot teaching response must include the strategy used.")

        expected_sequence_numbers = list(range(1, len(response.sections) + 1))
        actual_sequence_numbers = [section.sequence_number for section in response.sections]
        if actual_sequence_numbers != expected_sequence_numbers:
            validation_errors.append("Abbot response sections must be ordered with contiguous sequence numbers starting at 1.")

        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.abbot_response_validated",
                payload={
                    "session_id": response.session_id,
                    "response_type": response.response_type,
                    "is_valid": not validation_errors,
                    "validation_errors": validation_errors,
                },
            )
        )
        return validation_errors

    def _generate_response(
        self,
        request: AbbotTeachingRequest,
        response_type: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> AbbotTeachingResponse:
        package = request.grounded_teaching_package
        strategy = request.instructional_strategy
        sections = self._build_sections(package, strategy, response_type, metadata or {})
        return AbbotTeachingResponse(
            session_id=str(request.session.id),
            concept_title=package.primary_concept.content_concept_title,
            response_type=response_type,
            sections=sections,
            source_references=list(package.source_references),
            strategy_used=strategy.strategy_identifier,
            metadata={
                "generator": "deterministic_placeholder",
                "ai_provider": None,
                "hallucination_boundary": "uses_grounded_package_and_strategy_only",
            },
        )

    def _build_sections(
        self,
        package: GroundedTeachingPackage,
        strategy: InstructionalStrategy,
        response_type: str,
        metadata: dict[str, str],
    ) -> list[AbbotResponseSection]:
        source_reference_ids = self._source_reference_ids(package.source_references)
        primary = package.primary_instructional_evidence
        concept_title = package.primary_concept.content_concept_title
        objective = primary.learning_objective if primary else package.primary_concept.content_concept_learning_objective

        if response_type == AbbotResponseType.CLARIFICATION:
            learner_question = metadata.get("learner_question", "")
            return [
                AbbotResponseSection(
                    sequence_number=1,
                    title="Clarification Focus",
                    content=f"Clarifying {concept_title} using approved source evidence. Learner question: {learner_question}",
                    source_reference_ids=source_reference_ids[:1],
                ),
                AbbotResponseSection(
                    sequence_number=2,
                    title="Grounded Answer",
                    content=f"The safe answer stays within the learning objective: {objective}",
                    source_reference_ids=source_reference_ids,
                ),
            ]

        if response_type == AbbotResponseType.SUMMARY:
            return [
                AbbotResponseSection(
                    sequence_number=1,
                    title="Concept Summary",
                    content=f"Summary for {concept_title}: {package.primary_concept.content_concept_description}",
                    source_reference_ids=source_reference_ids[:1],
                ),
                AbbotResponseSection(
                    sequence_number=2,
                    title="Strategy Used",
                    content=f"This summary follows the {strategy.name} strategy without adding ungrounded claims.",
                    source_reference_ids=source_reference_ids,
                ),
            ]

        first_step = strategy.ordered_instructional_steps[0] if strategy.ordered_instructional_steps else None
        step_title = first_step.title if first_step else "Grounded Start"
        step_goal = first_step.instructional_goal if first_step else "Introduce the concept from source evidence."
        return [
            AbbotResponseSection(
                sequence_number=1,
                title="Grounded Concept",
                content=f"{concept_title}: {package.primary_concept.content_concept_description}",
                source_reference_ids=source_reference_ids[:1],
            ),
            AbbotResponseSection(
                sequence_number=2,
                title=step_title,
                content=f"{step_goal} Objective: {objective}",
                source_reference_ids=source_reference_ids,
            ),
            AbbotResponseSection(
                sequence_number=3,
                title="Source Boundary",
                content="This placeholder response uses only the grounded teaching package and instructional strategy.",
                source_reference_ids=source_reference_ids,
            ),
        ]

    def _add_abbot_message(
        self,
        session: PedagogicalSession,
        response: AbbotTeachingResponse,
        message_type: str,
    ) -> None:
        self.conversation_orchestrator.add_turn(
            session=session,
            sender_type=PedagogicalMessage.SenderType.ABBOT,
            message_type=message_type,
            content=self._render_response_for_session_message(response),
        )

    def _render_response_for_session_message(self, response: AbbotTeachingResponse) -> str:
        return "\n".join(section.content for section in response.sections)

    def _publish_response_generated(self, response: AbbotTeachingResponse) -> None:
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.abbot_response_generated",
                payload={
                    "session_id": response.session_id,
                    "response_type": response.response_type,
                    "strategy_used": response.strategy_used,
                    "section_count": len(response.sections),
                },
            )
        )

    def _source_reference_ids(self, source_references: list[SourceReference]) -> list[str]:
        return [f"{reference.academic_object_type}:{reference.object_id}" for reference in source_references]
