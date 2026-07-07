from __future__ import annotations

from typing import Any, Optional

from apps.core.events import BusinessEvent, EventPublisher
from apps.learning.domain.models import (
    ArielCompanion,
    CompanionInteraction,
    CompanionProfile,
    CompanionResponse,
    LearningCompanion,
    PedagogicalMessage,
    PedagogicalSession,
)
from apps.learning.services.conversation_orchestrator_service import ConversationOrchestratorService


class CompanionType:
    ARIEL = "ariel"
    DEBATE_PARTNER = "debate_partner"
    LAB_ASSISTANT = "lab_assistant"
    LANGUAGE_PARTNER = "language_partner"
    INTERVIEW_PANELIST = "interview_panelist"
    STUDY_BUDDY = "study_buddy"
    SYSTEM = "system"

    VALUES = {
        ARIEL,
        DEBATE_PARTNER,
        LAB_ASSISTANT,
        LANGUAGE_PARTNER,
        INTERVIEW_PANELIST,
        STUDY_BUDDY,
        SYSTEM,
    }


class CompanionInteractionType:
    PRESENCE = "presence"
    ENCOURAGEMENT = "encouragement"
    REFLECTION_PROMPT = "reflection_prompt"
    CLARIFICATION_PROMPT = "clarification_prompt"
    LEARNING_CHECK = "learning_check"
    SESSION_SUMMARY = "session_summary"
    SYSTEM = "system"

    VALUES = {
        PRESENCE,
        ENCOURAGEMENT,
        REFLECTION_PROMPT,
        CLARIFICATION_PROMPT,
        LEARNING_CHECK,
        SESSION_SUMMARY,
        SYSTEM,
    }


class LearningCompanionService:
    def __init__(
        self,
        event_publisher: Optional[EventPublisher] = None,
        conversation_orchestrator: Optional[ConversationOrchestratorService] = None,
    ) -> None:
        self.event_publisher = event_publisher or EventPublisher()
        self.conversation_orchestrator = conversation_orchestrator or ConversationOrchestratorService()
        self._companions: dict[str, LearningCompanion] = {}
        self._implementations: dict[str, Any] = {}
        self._session_companions: dict[str, set[str]] = {}
        self._register_default_companions()

    def register_companion(
        self,
        companion_type: str,
        name: str,
        description: str = "",
        supported_interaction_types: Optional[list[str]] = None,
        implementation: Any | None = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> LearningCompanion:
        self._validate_companion_type(companion_type)
        profile = CompanionProfile(
            companion_type=companion_type,
            name=name,
            description=description,
            supported_interaction_types=supported_interaction_types or [],
            metadata=metadata or {},
        )
        companion = LearningCompanion(companion_type=companion_type, profile=profile)
        self._companions[companion_type] = companion
        if implementation is not None:
            self._implementations[companion_type] = implementation
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.companion_registered",
                payload={"companion_type": companion_type, "name": name},
            )
        )
        return companion

    def get_companion(self, companion_type: str) -> LearningCompanion:
        return self._companions[companion_type]

    def list_companions(self) -> list[LearningCompanion]:
        return [self._companions[companion_type] for companion_type in sorted(self._companions)]

    def activate_companion_for_session(
        self,
        session: PedagogicalSession,
        companion_type: str,
    ) -> LearningCompanion:
        companion = self.get_companion(companion_type)
        session_id = self._session_id(session)
        self._session_companions.setdefault(session_id, set()).add(companion_type)
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.companion_activated",
                payload={"session_id": session_id, "companion_type": companion_type},
            )
        )
        return companion

    def deactivate_companion_for_session(
        self,
        session: PedagogicalSession,
        companion_type: str,
    ) -> None:
        session_id = self._session_id(session)
        self._session_companions.setdefault(session_id, set()).discard(companion_type)
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.companion_deactivated",
                payload={"session_id": session_id, "companion_type": companion_type},
            )
        )

    def generate_companion_response(
        self,
        session: PedagogicalSession,
        companion_type: str,
        interaction_type: str,
        context: Optional[dict[str, Any]] = None,
    ) -> CompanionResponse:
        self._validate_interaction_type(interaction_type)
        companion = self.get_companion(companion_type)
        interaction = CompanionInteraction(
            session_id=self._session_id(session),
            companion_type=companion_type,
            interaction_type=interaction_type,
            context=context or {},
        )
        implementation = self._implementations.get(companion_type)
        if implementation is None:
            response = self._default_response(interaction, companion)
        else:
            response = implementation.generate_response(interaction)

        recorded_response = self._record_response(session, response)
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.companion_response_generated",
                payload={
                    "session_id": recorded_response.session_id,
                    "companion_type": recorded_response.companion_type,
                    "interaction_type": recorded_response.interaction_type,
                    "recorded": recorded_response.recorded,
                },
            )
        )
        return recorded_response

    def list_session_companions(self, session: PedagogicalSession) -> list[LearningCompanion]:
        companion_types = sorted(self._session_companions.get(self._session_id(session), set()))
        return [self._companions[companion_type] for companion_type in companion_types]

    def _register_default_companions(self) -> None:
        ariel = ArielCompanion()
        self._companions[CompanionType.ARIEL] = LearningCompanion(
            companion_type=CompanionType.ARIEL,
            profile=ariel.profile,
        )
        self._implementations[CompanionType.ARIEL] = ariel

    def _default_response(
        self,
        interaction: CompanionInteraction,
        companion: LearningCompanion,
    ) -> CompanionResponse:
        return CompanionResponse(
            session_id=interaction.session_id,
            companion_type=interaction.companion_type,
            interaction_type=interaction.interaction_type,
            content=f"{companion.profile.name} is registered, but deterministic behavior is not yet implemented for this companion.",
            metadata={"source": "learning_companion_service"},
        )

    def _record_response(
        self,
        session: PedagogicalSession,
        response: CompanionResponse,
    ) -> CompanionResponse:
        sender_type = response.companion_type if response.companion_type in PedagogicalMessage.SenderType.values else PedagogicalMessage.SenderType.SYSTEM
        self.conversation_orchestrator.add_turn(
            session=session,
            sender_type=sender_type,
            message_type=response.interaction_type,
            content=response.content,
        )
        return CompanionResponse(
            session_id=response.session_id,
            companion_type=response.companion_type,
            interaction_type=response.interaction_type,
            content=response.content,
            recorded=True,
            metadata=response.metadata,
        )

    def _validate_companion_type(self, companion_type: str) -> None:
        if companion_type not in CompanionType.VALUES:
            raise ValueError(f"Unsupported companion type: {companion_type}.")

    def _validate_interaction_type(self, interaction_type: str) -> None:
        if interaction_type not in CompanionInteractionType.VALUES:
            raise ValueError(f"Unsupported companion interaction type: {interaction_type}.")

    def _session_id(self, session: PedagogicalSession) -> str:
        return str(session.id)
