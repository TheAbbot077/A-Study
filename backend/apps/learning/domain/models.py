from dataclasses import dataclass, field
from typing import Any
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.academic.domain.models import ContentConcept


@dataclass(frozen=True)
class ContextLearnerSnapshot:
    learner_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextCurriculumSnapshot:
    curriculum_id: str | None = None
    curriculum_name: str | None = None
    curriculum_unit_id: str | None = None
    curriculum_unit_title: str | None = None
    curriculum_unit_sequence_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextResourceSnapshot:
    learning_resource_id: str
    learning_resource_title: str
    resource_type: str
    subject_id: str | None = None
    subject_name: str | None = None
    curriculum: ContextCurriculumSnapshot = field(default_factory=ContextCurriculumSnapshot)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextSectionSnapshot:
    content_section_id: str
    content_section_title: str
    sequence_number: int | None = None
    review_status: str | None = None
    quality_status: str | None = None
    learning_resource: ContextResourceSnapshot | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextConceptSnapshot:
    content_concept_id: str
    content_concept_title: str
    content_concept_description: str
    content_concept_learning_objective: str
    sequence_number: int | None = None
    review_status: str | None = None
    quality_status: str | None = None
    content_section: ContextSectionSnapshot | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PedagogicalContext:
    learner: ContextLearnerSnapshot
    concept: ContextConceptSnapshot
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceReference:
    academic_object_type: str
    object_id: str
    title: str
    relationship: str
    sequence_number: int | None = None


@dataclass(frozen=True)
class PrimaryEvidence:
    source_reference: SourceReference
    title: str
    description: str
    learning_objective: str
    review_status: str | None = None
    quality_status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SupportingEvidence:
    source_reference: SourceReference
    title: str
    evidence_type: str
    review_status: str | None = None
    quality_status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GroundedTeachingPackage:
    pedagogical_context: PedagogicalContext
    primary_concept: ContextConceptSnapshot
    primary_instructional_evidence: PrimaryEvidence | None
    supporting_evidence: list[SupportingEvidence] = field(default_factory=list)
    source_references: list[SourceReference] = field(default_factory=list)
    review_status: str | None = None
    quality_status: str | None = None
    grounding_confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyStep:
    sequence_number: int
    title: str
    instructional_goal: str
    recommended_interaction: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InstructionalStrategy:
    strategy_identifier: str
    name: str
    pedagogical_objective: str
    ordered_instructional_steps: list[StrategyStep]
    estimated_complexity: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyRecommendation:
    grounded_teaching_package: GroundedTeachingPackage
    strategy: InstructionalStrategy
    rationale: str
    considered_strategy_identifiers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversationTurn:
    sequence_number: int
    sender_type: str
    message_type: str
    content: str
    timestamp: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversationWindow:
    turns: list[ConversationTurn]
    window_size: int
    supports_future_summarization: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversationContext:
    pedagogical_session: Any
    grounded_teaching_package: GroundedTeachingPackage
    instructional_strategy: InstructionalStrategy
    active_conversation_window: ConversationWindow
    current_turn_number: int
    current_instructional_step: StrategyStep | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AbbotResponseSection:
    sequence_number: int
    title: str
    content: str
    source_reference_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AbbotGenerationPlan:
    response_type: str
    grounded_teaching_package: GroundedTeachingPackage
    instructional_strategy: InstructionalStrategy
    conversation_context: ConversationContext
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AbbotTeachingRequest:
    session: Any
    pedagogical_context: PedagogicalContext
    grounded_teaching_package: GroundedTeachingPackage
    instructional_strategy: InstructionalStrategy
    conversation_context: ConversationContext
    generation_plan: AbbotGenerationPlan
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AbbotTeachingResponse:
    session_id: str
    concept_title: str
    response_type: str
    sections: list[AbbotResponseSection]
    source_references: list[SourceReference] = field(default_factory=list)
    strategy_used: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompanionProfile:
    companion_type: str
    name: str
    description: str
    supported_interaction_types: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LearningCompanion:
    companion_type: str
    profile: CompanionProfile
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompanionInteraction:
    session_id: str
    companion_type: str
    interaction_type: str
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompanionResponse:
    session_id: str
    companion_type: str
    interaction_type: str
    content: str
    recorded: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class ArielCompanion:
    companion_type = "ariel"

    profile = CompanionProfile(
        companion_type=companion_type,
        name="Ariel",
        description="A reflective learning companion that encourages presence, reflection, and session continuity.",
        supported_interaction_types=[
            "presence",
            "encouragement",
            "reflection_prompt",
            "session_summary",
        ],
        metadata={"implementation": "deterministic"},
    )

    def generate_response(self, interaction: CompanionInteraction) -> CompanionResponse:
        responses = {
            "presence": "I'm here with you. Let's stay focused on this learning moment.",
            "encouragement": "You're making progress. Take the next step carefully and keep your reasoning visible.",
            "reflection_prompt": "Pause for a moment: what part of this concept feels clearest, and what still feels uncertain?",
            "session_summary": "Session reflection: you engaged with the concept and preserved a path for the next learning step.",
        }
        content = responses.get(
            interaction.interaction_type,
            "I'm here as a learning companion, but this interaction type is not yet implemented for Ariel.",
        )
        return CompanionResponse(
            session_id=interaction.session_id,
            companion_type=self.companion_type,
            interaction_type=interaction.interaction_type,
            content=content,
            metadata={"source": "ariel_companion"},
        )


class PedagogicalState(models.TextChoices):
    CREATED = "created", "Created"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"
    ABANDONED = "abandoned", "Abandoned"


class PedagogicalSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pedagogical_sessions")
    content_concept = models.ForeignKey(ContentConcept, on_delete=models.CASCADE, related_name="pedagogical_sessions")
    status = models.CharField(max_length=50, choices=PedagogicalState.choices, default=PedagogicalState.CREATED)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "learning_pedagogical_session"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["learner"], name="learn_session_learner_idx"),
            models.Index(fields=["content_concept"], name="learn_session_concept_idx"),
            models.Index(fields=["status"], name="learn_session_status_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.learner_id} :: {self.content_concept_id} [{self.status}]"


class PedagogicalMessage(models.Model):
    class SenderType(models.TextChoices):
        LEARNER = "learner", "Learner"
        ABBOT = "abbot", "Abbot"
        ARIEL = "ariel", "Ariel"
        SYSTEM = "system", "System"

    class MessageType(models.TextChoices):
        EXPLANATION = "explanation", "Explanation"
        QUESTION = "question", "Question"
        RESPONSE = "response", "Response"
        CLARIFICATION = "clarification", "Clarification"
        SUMMARY = "summary", "Summary"
        LEARNER_QUESTION = "learner_question", "Learner Question"
        ACKNOWLEDGEMENT = "acknowledgement", "Acknowledgement"
        REFLECTION = "reflection", "Reflection"
        TRANSITION = "transition", "Transition"
        PRESENCE = "presence", "Presence"
        ENCOURAGEMENT = "encouragement", "Encouragement"
        REFLECTION_PROMPT = "reflection_prompt", "Reflection Prompt"
        CLARIFICATION_PROMPT = "clarification_prompt", "Clarification Prompt"
        LEARNING_CHECK = "learning_check", "Learning Check"
        SESSION_SUMMARY = "session_summary", "Session Summary"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedagogical_session = models.ForeignKey(PedagogicalSession, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=50, choices=SenderType.choices)
    message_type = models.CharField(max_length=50, choices=MessageType.choices)
    content = models.TextField()
    sequence_number = models.PositiveIntegerField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "learning_pedagogical_message"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["pedagogical_session", "sequence_number"], name="unique_pedagogical_session_sequence"),
            models.CheckConstraint(condition=models.Q(sequence_number__gte=1), name="pedagogical_message_sequence_gte_1"),
        ]
        indexes = [
            models.Index(fields=["pedagogical_session"], name="learn_msg_session_idx"),
            models.Index(fields=["sender_type"], name="learn_msg_sender_idx"),
            models.Index(fields=["message_type"], name="learn_msg_type_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.pedagogical_session_id} #{self.sequence_number}"


__all__ = [
    "PedagogicalContext",
    "ContextConceptSnapshot",
    "ContextSectionSnapshot",
    "ContextResourceSnapshot",
    "ContextCurriculumSnapshot",
    "ContextLearnerSnapshot",
    "GroundedTeachingPackage",
    "PrimaryEvidence",
    "SupportingEvidence",
    "SourceReference",
    "InstructionalStrategy",
    "StrategyStep",
    "StrategyRecommendation",
    "ConversationContext",
    "ConversationTurn",
    "ConversationWindow",
    "AbbotTeachingRequest",
    "AbbotTeachingResponse",
    "AbbotResponseSection",
    "AbbotGenerationPlan",
    "LearningCompanion",
    "CompanionInteraction",
    "CompanionResponse",
    "CompanionProfile",
    "ArielCompanion",
    "PedagogicalState",
    "PedagogicalSession",
    "PedagogicalMessage",
]
