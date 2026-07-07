from __future__ import annotations

from typing import Optional

from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.learning.domain.models import (
    ConversationContext,
    ConversationTurn,
    ConversationWindow,
    InstructionalStrategy,
    PedagogicalMessage,
    PedagogicalSession,
    StrategyStep,
)
from apps.learning.services.context_assembly_service import ContextAssemblyService
from apps.learning.services.grounding_service import GroundingService
from apps.learning.services.instructional_strategy_service import InstructionalStrategyService
from apps.learning.services.pedagogical_session_service import PedagogicalSessionService


class ConversationInteractionType:
    EXPLANATION = "explanation"
    LEARNER_QUESTION = "learner_question"
    CLARIFICATION = "clarification"
    ACKNOWLEDGEMENT = "acknowledgement"
    REFLECTION = "reflection"
    SUMMARY = "summary"
    TRANSITION = "transition"
    SYSTEM = "system"

    VALUES = {
        EXPLANATION,
        LEARNER_QUESTION,
        CLARIFICATION,
        ACKNOWLEDGEMENT,
        REFLECTION,
        SUMMARY,
        TRANSITION,
        SYSTEM,
    }


class ConversationOrchestratorService:
    DEFAULT_WINDOW_SIZE = 12

    def __init__(
        self,
        event_publisher: Optional[EventPublisher] = None,
        context_assembly_service: Optional[ContextAssemblyService] = None,
        grounding_service: Optional[GroundingService] = None,
        strategy_service: Optional[InstructionalStrategyService] = None,
        session_service: Optional[PedagogicalSessionService] = None,
    ) -> None:
        self.event_publisher = event_publisher or EventPublisher()
        self.context_assembly_service = context_assembly_service or ContextAssemblyService()
        self.grounding_service = grounding_service or GroundingService()
        self.strategy_service = strategy_service or InstructionalStrategyService()
        self.session_service = session_service or PedagogicalSessionService()

    def initialize_conversation(self, session: PedagogicalSession) -> ConversationContext:
        context = self.build_conversation_context(session)
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.conversation_initialized",
                payload={
                    "session_id": str(session.id),
                    "current_turn_number": context.current_turn_number,
                    "strategy_identifier": context.instructional_strategy.strategy_identifier,
                },
            )
        )
        return context

    def build_conversation_context(self, session: PedagogicalSession) -> ConversationContext:
        pedagogical_context = self.context_assembly_service.assemble_for_session(session)
        grounded_teaching_package = self.grounding_service.build_grounding_package(pedagogical_context)
        strategy_recommendation = self.strategy_service.select_strategy(grounded_teaching_package)
        turns = self.list_conversation_turns(session)
        window = self._build_window(turns, self.DEFAULT_WINDOW_SIZE)
        current_turn_number = len(turns)
        return ConversationContext(
            pedagogical_session=session,
            grounded_teaching_package=grounded_teaching_package,
            instructional_strategy=strategy_recommendation.strategy,
            active_conversation_window=window,
            current_turn_number=current_turn_number,
            current_instructional_step=self._current_instructional_step(
                strategy_recommendation.strategy,
                current_turn_number,
            ),
            metadata={"source": "conversation_orchestrator_service"},
        )

    def add_turn(
        self,
        session: PedagogicalSession,
        sender_type: str,
        message_type: str,
        content: str,
    ) -> ConversationTurn:
        message = self.session_service.add_message(
            session=session,
            sender_type=sender_type,
            message_type=message_type,
            content=content,
            metadata={"source": "conversation_orchestrator_service"},
        )
        turn = self._turn_from_message(message)
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.turn_added",
                payload={
                    "session_id": str(session.id),
                    "sequence_number": turn.sequence_number,
                    "sender_type": turn.sender_type,
                    "message_type": turn.message_type,
                },
            )
        )
        return turn

    def next_expected_interaction(self, session: PedagogicalSession) -> str:
        turns = self.list_conversation_turns(session)
        if not turns:
            return ConversationInteractionType.EXPLANATION

        last_turn = turns[-1]
        if last_turn.message_type == ConversationInteractionType.LEARNER_QUESTION:
            return ConversationInteractionType.CLARIFICATION
        if last_turn.sender_type == PedagogicalMessage.SenderType.LEARNER:
            return ConversationInteractionType.ACKNOWLEDGEMENT
        if last_turn.message_type == ConversationInteractionType.SUMMARY:
            return ConversationInteractionType.SYSTEM
        if len(turns) >= self.DEFAULT_WINDOW_SIZE:
            return ConversationInteractionType.SUMMARY
        return ConversationInteractionType.REFLECTION

    def trim_conversation_window(
        self,
        session: PedagogicalSession,
        max_turns: int | None = None,
    ) -> ConversationWindow:
        window_size = max_turns or self.DEFAULT_WINDOW_SIZE
        turns = self.list_conversation_turns(session)
        window = self._build_window(turns, window_size)
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.window_trimmed",
                payload={
                    "session_id": str(session.id),
                    "window_size": window.window_size,
                    "turn_count": len(window.turns),
                    "total_turn_count": len(turns),
                },
            )
        )
        return window

    def list_conversation_turns(self, session: PedagogicalSession) -> list[ConversationTurn]:
        messages = self.session_service.list_messages(session)
        return [self._turn_from_message(message) for message in messages]

    def _build_window(self, turns: list[ConversationTurn], window_size: int) -> ConversationWindow:
        if window_size < 1:
            raise ValueError("Conversation window size must be greater than or equal to 1.")
        return ConversationWindow(
            turns=turns[-window_size:],
            window_size=window_size,
            metadata={"summarization_status": "not_implemented"},
        )

    def _turn_from_message(self, message) -> ConversationTurn:
        return ConversationTurn(
            sequence_number=message.sequence_number,
            sender_type=message.sender_type,
            message_type=message.message_type,
            content=message.content,
            timestamp=getattr(message, "created_at", None) or timezone.now(),
            metadata=getattr(message, "metadata", {}) or {},
        )

    def _current_instructional_step(
        self,
        instructional_strategy: InstructionalStrategy,
        current_turn_number: int,
    ) -> StrategyStep | None:
        if not instructional_strategy.ordered_instructional_steps:
            return None
        step_index = min(current_turn_number, len(instructional_strategy.ordered_instructional_steps) - 1)
        return instructional_strategy.ordered_instructional_steps[step_index]
