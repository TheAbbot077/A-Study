"""
Ariel application services enforcing constitutional rules.

All constitutional rules belong here. These services are the only path
through which Ariel memory may be created, reinforced, corrected, or forgotten.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.ariel.domain.models import (
    ArielCapability,
    ArielConstitution,
    ArielCorrectionRecord,
    ArielIdentity,
    ArielIdentityStatus,
    ArielKnowledgeUnit,
    ArielMemoryRecord,
    ArielMisconception,
    ArielRelationship,
    ArielReinforcementRecord,
    ArielTeachBackInteraction,
    ArielTeachingSession,
    ArielTeachingTurn,
    TeachBackIntensity,
    TeachBackInteractionStatus,
    TeachBackInteractionType,
    TeachingInputProvenance,
    TeachingTransformationStatus,
    TeachingTransformationType,
    TeachingTurnDisposition,
    ArielUserCapability,
    ConsentState,
    ConstitutionRule,
    InstitutionalVisibility,
    KnowledgeProvenance,
    MemoryState,
    TeachingTurnActor,
)


class ConstitutionEnforcementService:
    """Enforces Ariel constitutional rules at the application layer."""

    @staticmethod
    def get_active_constitution() -> ArielConstitution:
        constitution = ArielConstitution.objects.filter(is_active=True).first()
        if not constitution:
            raise ValidationError("No active Ariel constitution found.", code="ARIEL_NO_CONSTITUTION")
        return constitution

    @staticmethod
    def validate_learner_teaching(constitution: ArielConstitution) -> None:
        """Validate that knowledge creation follows learner-only provenance."""
        if not constitution.has_rule(ConstitutionRule.ARIEL_LEARNS_ONLY_FROM_LEARNER):
            raise ValidationError("Constitution requires learner-only teaching.", code="ARIEL_CONSTITUTION_VIOLATION")

    @staticmethod
    def validate_no_retrieval_access(constitution: ArielConstitution) -> None:
        if not constitution.has_rule(ConstitutionRule.ARIEL_DOES_NOT_ACCESS_RETRIEVAL):
            raise ValidationError("Ariel must not access retrieval.", code="ARIEL_CONSTITUTION_VIOLATION")

    @staticmethod
    def validate_no_curriculum_access(constitution: ArielConstitution) -> None:
        if not constitution.has_rule(ConstitutionRule.ARIEL_DOES_NOT_ACCESS_CURRICULUM):
            raise ValidationError("Ariel must not access curriculum.", code="ARIEL_CONSTITUTION_VIOLATION")

    @staticmethod
    def validate_no_answer_key_access(constitution: ArielConstitution) -> None:
        if not constitution.has_rule(ConstitutionRule.ARIEL_DOES_NOT_ACCESS_ANSWER_KEYS):
            raise ValidationError("Ariel must not access answer keys.", code="ARIEL_CONSTITUTION_VIOLATION")

    @staticmethod
    def validate_memory_provenance(constitution: ArielConstitution, provenance: str) -> None:
        if not constitution.has_rule(ConstitutionRule.ARIEL_MEMORY_REQUIRES_PROVENANCE):
            raise ValidationError("Constitution requires memory provenance.", code="ARIEL_CONSTITUTION_VIOLATION")
        if provenance not in KnowledgeProvenance.values:
            raise ValidationError("Provenance must be learner-originated.", code="ARIEL_PROVENANCE_INVALID")

    @staticmethod
    def reject_curriculum_injection() -> None:
        """Explicitly reject attempts to create Ariel memory from curriculum."""
        raise ValidationError(
            "Ariel memory cannot originate from curriculum.",
            code="ARIEL_CURRICULUM_INJECTION_REJECTED",
        )

    @staticmethod
    def reject_retrieval_injection() -> None:
        """Explicitly reject attempts to create Ariel memory from retrieval."""
        raise ValidationError(
            "Ariel memory cannot originate from retrieval.",
            code="ARIEL_RETRIEVAL_INJECTION_REJECTED",
        )

    @staticmethod
    def reject_abbot_injection() -> None:
        """Explicitly reject attempts to create Ariel memory from Abbot."""
        raise ValidationError(
            "Ariel memory cannot originate from Abbot.",
            code="ARIEL_ABBOT_INJECTION_REJECTED",
        )

    @staticmethod
    def reject_answer_key_injection() -> None:
        """Explicitly reject attempts to create Ariel memory from answer keys."""
        raise ValidationError(
            "Ariel memory cannot originate from answer keys.",
            code="ARIEL_ANSWER_KEY_INJECTION_REJECTED",
        )


class ArielIdentityService:
    """Service for Ariel identity lifecycle management."""

    @staticmethod
    @transaction.atomic
    def create_identity(learner_id, constitution=None, institution_id=None, display_name="Ariel"):
        constitution = constitution or ConstitutionEnforcementService.get_active_constitution()

        # Check for existing active Ariel
        existing = ArielIdentity.objects.filter(
            learner_id=learner_id,
            status=ArielIdentityStatus.ACTIVE,
        ).first()
        if existing:
            raise ValidationError("Learner already has an active Ariel.", code="ARIEL_ALREADY_EXISTS")

        identity = ArielIdentity.objects.create(
            learner_id=learner_id,
            constitution=constitution,
            institution_id=institution_id,
            display_name=display_name,
        )

        # Create relationship
        ArielRelationship.objects.create(
            identity=identity,
            learner_id=learner_id,
            consent_state=ConsentState.PENDING,
            institutional_visibility=InstitutionalVisibility.PRIVATE,
        )

        # Grant learner capabilities
        learner_caps = [
            ArielCapability.ARIEL_USE,
            ArielCapability.ARIEL_VIEW_MEMORY,
            ArielCapability.ARIEL_CORRECT_MEMORY,
            ArielCapability.ARIEL_FORGET_MEMORY,
            ArielCapability.ARIEL_RESET,
            ArielCapability.ARIEL_EXPORT,
            ArielCapability.ARIEL_SUSPEND,
        ]
        for cap in learner_caps:
            ArielUserCapability.objects.create(
                user_id=learner_id,
                identity=identity,
                capability_code=cap,
                granted_by_id=learner_id,
            )

        return identity

    @staticmethod
    def activate_identity(identity: ArielIdentity):
        identity.activate()
        identity.save()
        return identity

    @staticmethod
    def suspend_identity(identity: ArielIdentity):
        identity.suspend()
        identity.save()
        return identity

    @staticmethod
    def archive_identity(identity: ArielIdentity):
        identity.archive()
        identity.save()
        return identity

    @staticmethod
    def reset_identity(identity: ArielIdentity):
        """Reset Ariel memory while preserving audit history."""
        # Mark all knowledge as forgotten (preserves records)
        knowledge_units = ArielKnowledgeUnit.objects.filter(identity=identity).exclude(
            memory_state__in=[MemoryState.FORGOTTEN, MemoryState.RETRACTED]
        )
        for ku in knowledge_units:
            old_state = ku.memory_state
            ku.forget()
            ku.save()
            ArielMemoryRecord.objects.create(
                identity=identity,
                knowledge_unit=ku,
                learner_id=identity.learner_id,
                previous_state=old_state,
                new_state=MemoryState.FORGOTTEN,
                previous_confidence=ku.confidence,
                new_confidence=ku.confidence,
                transition_reason="ARIEL_RESET",
                provenance=KnowledgeProvenance.LEARNER_TEACHING,
                metadata={"reset": True},
            )
        return identity


class ArielTeachingService:
    """Service for governed learner teaching sessions and memory creation."""

    @staticmethod
    @transaction.atomic
    def start_teaching_session(identity: ArielIdentity, learner_id, learning_journey_id=None, subject_id=None, concept_reference=""):
        if identity.learner_id != learner_id:
            raise ValidationError("Only the owning learner can teach Ariel.", code="ARIEL_NOT_OWNER")
        if identity.status != ArielIdentityStatus.ACTIVE:
            raise ValidationError("Ariel must be active to start teaching.", code="ARIEL_NOT_ACTIVE")

        constitution = identity.constitution
        ConstitutionEnforcementService.validate_learner_teaching(constitution)

        return ArielTeachingSession.objects.create(
            identity=identity,
            learner_id=learner_id,
            constitution=constitution,
            learning_journey_id=learning_journey_id,
            subject_id=subject_id,
            concept_reference=concept_reference,
        )

    @staticmethod
    @transaction.atomic
    def add_teaching_turn(session: ArielTeachingSession, actor, content, disposition=TeachingTurnDisposition.CONVERSATION):
        # Get next sequence number
        last_turn = session.turns.order_by("-sequence_number").first()
        next_seq = (last_turn.sequence_number + 1) if last_turn else 1

        provenance = ""
        if disposition in [TeachingTurnDisposition.TEACHING, TeachingTurnDisposition.REINFORCEMENT]:
            provenance = KnowledgeProvenance.LEARNER_TEACHING
        elif disposition == TeachingTurnDisposition.CORRECTION:
            provenance = KnowledgeProvenance.LEARNER_CORRECTION

        return ArielTeachingTurn.objects.create(
            session=session,
            actor=actor,
            content=content,
            sequence_number=next_seq,
            disposition=disposition,
            provenance=provenance,
        )

    @staticmethod
    @transaction.atomic
    def create_knowledge_from_teaching(
        session: ArielTeachingSession,
        teaching_turn: ArielTeachingTurn,
        normalized_statement: str,
        confidence: float = 0.5,
        subject_id=None,
        concept_reference: str = "",
    ):
        """Create a knowledge unit from explicit learner teaching only."""
        constitution = session.constitution

        # Constitutional enforcement
        ConstitutionEnforcementService.validate_learner_teaching(constitution)
        ConstitutionEnforcementService.validate_memory_provenance(constitution, KnowledgeProvenance.LEARNER_TEACHING)

        # Verify the teaching turn is actually a teaching disposition
        if teaching_turn.disposition not in [
            TeachingTurnDisposition.TEACHING,
            TeachingTurnDisposition.REINFORCEMENT,
            TeachingTurnDisposition.CORRECTION,
        ]:
            raise ValidationError(
                "Knowledge can only be created from teaching turns, not conversation.",
                code="ARIEL_NOT_TEACHING_TURN",
            )

        # Verify the turn belongs to the session
        if teaching_turn.session_id != session.id:
            raise ValidationError("Teaching turn must belong to the session.", code="ARIEL_TURN_SESSION_MISMATCH")

        knowledge = ArielKnowledgeUnit.objects.create(
            identity=session.identity,
            learner_id=session.learner_id,
            teaching_turn=teaching_turn,
            session=session,
            normalized_statement=normalized_statement,
            confidence=confidence,
            memory_state=MemoryState.NEW,
            provenance=KnowledgeProvenance.LEARNER_TEACHING,
            subject_id=subject_id,
            concept_reference=concept_reference,
        )

        # Record memory transition
        ArielMemoryRecord.objects.create(
            identity=session.identity,
            knowledge_unit=knowledge,
            learner_id=session.learner_id,
            previous_state=MemoryState.NEW,
            new_state=MemoryState.NEW,
            new_confidence=confidence,
            transition_reason="KNOWLEDGE_CREATED",
            provenance=KnowledgeProvenance.LEARNER_TEACHING,
        )

        return knowledge

    @staticmethod
    @transaction.atomic
    def reinforce_knowledge(knowledge: ArielKnowledgeUnit, teaching_turn: ArielTeachingTurn, new_confidence=None):
        """Reinforce existing knowledge through repeated teaching."""
        old_state = knowledge.memory_state
        old_confidence = knowledge.confidence

        knowledge.reinforce(new_confidence=new_confidence)
        knowledge.save()

        # Record reinforcement
        ArielReinforcementRecord.objects.create(
            identity=knowledge.identity,
            knowledge_unit=knowledge,
            learner_id=knowledge.learner_id,
            teaching_turn=teaching_turn,
            previous_confidence=old_confidence,
            updated_confidence=knowledge.confidence,
            previous_state=old_state,
            new_state=knowledge.memory_state,
        )

        # Record memory transition
        ArielMemoryRecord.objects.create(
            identity=knowledge.identity,
            knowledge_unit=knowledge,
            learner_id=knowledge.learner_id,
            previous_state=old_state,
            new_state=knowledge.memory_state,
            previous_confidence=old_confidence,
            new_confidence=knowledge.confidence,
            transition_reason="REINFORCED",
            provenance=KnowledgeProvenance.LEARNER_REINFORCEMENT,
        )

        return knowledge

    @staticmethod
    @transaction.atomic
    def correct_knowledge(
        old_knowledge: ArielKnowledgeUnit,
        teaching_turn: ArielTeachingTurn,
        new_normalized_statement: str,
        correction_reason: str = "",
        confidence: float = 0.5,
    ):
        """Correct existing knowledge, preserving history."""
        session = teaching_turn.session

        # Create replacement knowledge
        new_knowledge = ArielKnowledgeUnit.objects.create(
            identity=old_knowledge.identity,
            learner_id=old_knowledge.learner_id,
            teaching_turn=teaching_turn,
            session=session,
            normalized_statement=new_normalized_statement,
            confidence=confidence,
            memory_state=MemoryState.NEW,
            provenance=KnowledgeProvenance.LEARNER_CORRECTION,
            subject_id=old_knowledge.subject_id,
            concept_reference=old_knowledge.concept_reference,
        )

        # Supersede old knowledge
        old_state = old_knowledge.memory_state
        old_knowledge.supersede(successor=new_knowledge)
        old_knowledge.save()

        # Create correction record
        ArielCorrectionRecord.objects.create(
            identity=old_knowledge.identity,
            learner_id=old_knowledge.learner_id,
            superseded_knowledge=old_knowledge,
            replacement_knowledge=new_knowledge,
            teaching_turn=teaching_turn,
            correction_reason=correction_reason,
        )

        # Record memory transition
        ArielMemoryRecord.objects.create(
            identity=old_knowledge.identity,
            knowledge_unit=old_knowledge,
            learner_id=old_knowledge.learner_id,
            previous_state=old_state,
            new_state=MemoryState.SUPERSEDED,
            transition_reason="CORRECTED",
            provenance=KnowledgeProvenance.LEARNER_CORRECTION,
        )

        return new_knowledge

    @staticmethod
    @transaction.atomic
    def forget_knowledge(knowledge: ArielKnowledgeUnit, reason: str = "LEARNER_REQUEST"):
        """Initiate forgetting for a knowledge unit."""
        old_state = knowledge.memory_state
        old_confidence = knowledge.confidence

        knowledge.forget()
        knowledge.save()

        ArielMemoryRecord.objects.create(
            identity=knowledge.identity,
            knowledge_unit=knowledge,
            learner_id=knowledge.learner_id,
            previous_state=old_state,
            new_state=MemoryState.FORGOTTEN,
            previous_confidence=old_confidence,
            new_confidence=old_confidence,
            transition_reason=reason,
            provenance=KnowledgeProvenance.LEARNER_TEACHING,
        )

        return knowledge

    @staticmethod
    @transaction.atomic
    def mark_contradiction(knowledge: ArielKnowledgeUnit, conflicting_knowledge: ArielKnowledgeUnit):
        """Mark two knowledge units as conflicting, preserving both."""
        knowledge.mark_conflicted()
        knowledge.save()
        conflicting_knowledge.mark_conflicted()
        conflicting_knowledge.save()

        ArielMemoryRecord.objects.create(
            identity=knowledge.identity,
            knowledge_unit=knowledge,
            learner_id=knowledge.learner_id,
            previous_state=knowledge.memory_state,
            new_state=MemoryState.CONFLICTED,
            transition_reason="CONTRADICTION_DETECTED",
            provenance=KnowledgeProvenance.LEARNER_TEACHING,
            metadata={"conflicting_knowledge_id": str(conflicting_knowledge.id)},
        )

        return knowledge

    @staticmethod
    @transaction.atomic
    def record_misconception(knowledge: ArielKnowledgeUnit, original_explanation: str, resulting_belief: str):
        """Record a misconception, preserving it as educational history."""
        knowledge.mark_misconceived()
        knowledge.save()

        misconception = ArielMisconception.objects.create(
            identity=knowledge.identity,
            knowledge_unit=knowledge,
            learner_id=knowledge.learner_id,
            original_explanation=original_explanation,
            resulting_belief=resulting_belief,
            current_state=MemoryState.MISCONCEIVED,
        )

        return misconception

    @staticmethod
    @transaction.atomic
    def retract_knowledge(knowledge: ArielKnowledgeUnit):
        """Retract a knowledge unit."""
        old_state = knowledge.memory_state
        knowledge.retract()
        knowledge.save()

        ArielMemoryRecord.objects.create(
            identity=knowledge.identity,
            knowledge_unit=knowledge,
            learner_id=knowledge.learner_id,
            previous_state=old_state,
            new_state=MemoryState.RETRACTED,
            transition_reason="LEARNER_RETRACTED",
            provenance=KnowledgeProvenance.LEARNER_TEACHING,
        )

        return knowledge


class ArielAuthorizationService:
    """Authorization service for Ariel capabilities."""

    @staticmethod
    def has_capability(user_id, identity_id, capability_code):
        return ArielUserCapability.objects.filter(
            user_id=user_id,
            identity_id=identity_id,
            capability_code=capability_code,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).exists()

    @staticmethod
    def get_user_capabilities(user_id, identity_id):
        return list(
            ArielUserCapability.objects.filter(
                user_id=user_id,
                identity_id=identity_id,
            ).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            ).values_list("capability_code", flat=True)
        )

    @staticmethod
    def can_view_memory(user_id, identity_id):
        return ArielAuthorizationService.has_capability(user_id, identity_id, ArielCapability.ARIEL_VIEW_MEMORY)

    @staticmethod
    def can_correct_memory(user_id, identity_id):
        return ArielAuthorizationService.has_capability(user_id, identity_id, ArielCapability.ARIEL_CORRECT_MEMORY)

    @staticmethod
    def can_forget_memory(user_id, identity_id):
        return ArielAuthorizationService.has_capability(user_id, identity_id, ArielCapability.ARIEL_FORGET_MEMORY)

    @staticmethod
    def can_reset(user_id, identity_id):
        return ArielAuthorizationService.has_capability(user_id, identity_id, ArielCapability.ARIEL_RESET)

    @staticmethod
    def can_export(user_id, identity_id):
        return ArielAuthorizationService.has_capability(user_id, identity_id, ArielCapability.ARIEL_EXPORT)

    @staticmethod
    def can_suspend(user_id, identity_id):
        return ArielAuthorizationService.has_capability(user_id, identity_id, ArielCapability.ARIEL_SUSPEND)

    @staticmethod
    def is_learner_owner(user_id, identity_id):
        identity = ArielIdentity.objects.filter(pk=identity_id).first()
        return identity and identity.learner_id == user_id

    @staticmethod
    def can_institution_access_transcripts(user_id, identity_id):
        """Institutions can never access Ariel transcripts by default."""
        return False

    @staticmethod
    def can_admin_browse_transcripts(user_id, identity_id):
        """Administrators can never browse Ariel transcripts."""
        return False


class ArielTeachBackTemplateRegistry:
    """Versioned learner-safe prompt templates for teach-back interactions."""

    TEMPLATES = {
        TeachBackInteractionType.RESTATEMENT: {
            "template_key": "TEACH_BACK_RESTATEMENT_V1",
            "template_version": "1",
            "prompt_text": "Can you explain that again in different words?",
        },
        TeachBackInteractionType.NEW_EXAMPLE: {
            "template_key": "TEACH_BACK_NEW_EXAMPLE_V1",
            "template_version": "1",
            "prompt_text": "Can you give me a different example?",
        },
        TeachBackInteractionType.DRAW_OR_DIAGRAM: {
            "template_key": "TEACH_BACK_DIAGRAM_V1",
            "template_version": "1",
            "prompt_text": "Can you show me that with a diagram?",
        },
        TeachBackInteractionType.LABEL_DIAGRAM: {
            "template_key": "TEACH_BACK_LABEL_V1",
            "template_version": "1",
            "prompt_text": "Can you label the important parts so I know what I am looking at?",
        },
        TeachBackInteractionType.COMPARE_CASES: {
            "template_key": "TEACH_BACK_COMPARE_V1",
            "template_version": "1",
            "prompt_text": "I am mixing those ideas up. Can you compare them for me?",
        },
        TeachBackInteractionType.WHAT_IF: {
            "template_key": "TEACH_BACK_WHAT_IF_V1",
            "template_version": "1",
            "prompt_text": "What would change if one condition were removed, and why?",
        },
        TeachBackInteractionType.CORRECT_ARIEL: {
            "template_key": "TEACH_BACK_CORRECT_ARIEL_V1",
            "template_version": "1",
            "prompt_text": "I think I have understood part of this incorrectly. Can you correct me?",
        },
        TeachBackInteractionType.RETEACH_AFTER_DELAY: {
            "template_key": "TEACH_BACK_RETEACH_V1",
            "template_version": "1",
            "prompt_text": "I do not remember this as clearly now. Can you teach it to me again?",
        },
        TeachBackInteractionType.UNFAMILIAR_APPLICATION: {
            "template_key": "TEACH_BACK_APPLICATION_V1",
            "template_version": "1",
            "prompt_text": "Can you apply that idea to a new situation?",
        },
        TeachBackInteractionType.CLARIFY_TERM: {
            "template_key": "TEACH_BACK_CLARIFY_TERM_V1",
            "template_version": "1",
            "prompt_text": "Can you clarify the term using a simple explanation?",
        },
        TeachBackInteractionType.EXPLAIN_STEP: {
            "template_key": "TEACH_BACK_EXPLAIN_STEP_V1",
            "template_version": "1",
            "prompt_text": "Can you explain the next step carefully?",
        },
        TeachBackInteractionType.CONNECT_IDEAS: {
            "template_key": "TEACH_BACK_CONNECT_IDEAS_V1",
            "template_version": "1",
            "prompt_text": "Can you connect those ideas for me?",
        },
        TeachBackInteractionType.RESOLVE_CONTRADICTION: {
            "template_key": "TEACH_BACK_RESOLVE_CONTRADICTION_V1",
            "template_version": "1",
            "prompt_text": "These ideas seem to conflict. Can you help resolve that contradiction?",
        },
    }

    @classmethod
    def get(cls, strategy: str) -> dict:
        return cls.TEMPLATES[strategy]

    @classmethod
    def list(cls) -> list[dict]:
        return [
            {"strategy": strategy.value if hasattr(strategy, "value") else str(strategy), **template}
            for strategy, template in cls.TEMPLATES.items()
        ]


class ArielProductiveStrugglePolicy:
    """Deterministic policy for choosing how much effort to request."""

    @staticmethod
    def resolve_intensity(*, source_memory_state="", source_memory_confidence=None, memory_age_days=None, recent_interactions=0, unresolved_interactions=0):
        if source_memory_state in {MemoryState.CONFLICTED, MemoryState.MISCONCEIVED}:
            return TeachBackIntensity.DEEP
        if source_memory_state == MemoryState.FORGOTTEN:
            return TeachBackIntensity.STANDARD
        if source_memory_state == MemoryState.FRAGILE:
            return TeachBackIntensity.STANDARD
        if unresolved_interactions >= 2 or recent_interactions >= 3:
            return TeachBackIntensity.DEEP
        if source_memory_confidence is not None and float(source_memory_confidence) < 0.55:
            return TeachBackIntensity.DEEP
        if memory_age_days is not None and memory_age_days >= 30:
            return TeachBackIntensity.STANDARD
        return TeachBackIntensity.LIGHT if source_memory_confidence is not None and float(source_memory_confidence) >= 0.85 else TeachBackIntensity.STANDARD


class ResolveTeachingTransformationService:
    """Resolve deterministic transformations for pasted or referenced teaching input."""

    @staticmethod
    def execute(*, input_provenance=TeachingInputProvenance.UNKNOWN, artefact_type="", authorship_classification="", concept_reference=""):
        if input_provenance in {
            TeachingInputProvenance.PASTED_TEXT,
            TeachingInputProvenance.VOICE_TRANSCRIPT,
        }:
            return {
                "requires_transformation": True,
                "transformation_type": TeachingTransformationType.RESTATED_EXPLANATION.value,
                "reason_code": "TEXT_RESTATED",
            }
        if input_provenance == TeachingInputProvenance.STUDY_LAB_ARTEFACT:
            normalized_type = (artefact_type or "").lower()
            if normalized_type in {"diagram", "concept_map", "whiteboard_snapshot"}:
                return {
                    "requires_transformation": True,
                    "transformation_type": TeachingTransformationType.LABELLING.value,
                    "reason_code": "DIAGRAM_LABELLED",
                }
            if normalized_type in {"comparison_table", "table", "graph"}:
                return {
                    "requires_transformation": True,
                    "transformation_type": TeachingTransformationType.COMPARISON.value,
                    "reason_code": "ARTEFACT_INTERPRETED",
                }
            return {
                "requires_transformation": True,
                "transformation_type": TeachingTransformationType.APPLICATION.value,
                "reason_code": "ARTEFACT_APPLIED",
            }
        if input_provenance == TeachingInputProvenance.IMPORTED_ARTEFACT:
            return {
                "requires_transformation": True,
                "transformation_type": TeachingTransformationType.ORIGINAL_EXAMPLE.value,
                "reason_code": "IMPORTED_ARTEFACT_REFRAMED",
            }
        if authorship_classification in {"AI_GENERATED", "TOOL_GENERATED"}:
            return {
                "requires_transformation": True,
                "transformation_type": TeachingTransformationType.APPLICATION.value,
                "reason_code": "NON_LEARNER_AUTHORED_REFRAMED",
            }
        if "diagram" in (concept_reference or "").lower():
            return {
                "requires_transformation": True,
                "transformation_type": TeachingTransformationType.DIAGRAM.value,
                "reason_code": "VISUAL_CONTEXT",
            }
        return {
            "requires_transformation": False,
            "transformation_type": None,
            "reason_code": "NO_TRANSFORMATION_REQUIRED",
        }


class ResolveArielTeachBackStrategyService:
    """Deterministically resolve a teach-back strategy from Ariel-owned state."""

    @staticmethod
    def execute(
        *,
        source_memory_unit: ArielKnowledgeUnit | None = None,
        concept_reference: str = "",
        input_provenance: str = TeachingInputProvenance.UNKNOWN,
        learner_approved_artefact_type: str = "",
        authorship_classification: str = "",
        related_memory_count: int = 0,
        recent_interactions: int = 0,
        unresolved_interactions: int = 0,
        prior_strategy_codes: list[str] | None = None,
        memory_age_days: int | None = None,
    ) -> dict:
        prior_strategy_codes = prior_strategy_codes or []
        source_state = source_memory_unit.memory_state if source_memory_unit else ""
        source_confidence = source_memory_unit.confidence if source_memory_unit else None
        transformation = ResolveTeachingTransformationService.execute(
            input_provenance=input_provenance,
            artefact_type=learner_approved_artefact_type,
            authorship_classification=authorship_classification,
            concept_reference=concept_reference,
        )

        normalized_concept = (concept_reference or "").lower()
        normalized_artefact_type = (learner_approved_artefact_type or "").lower()

        strategy = TeachBackInteractionType.NEW_EXAMPLE
        reason_code = "DEFAULT_NEW_EXAMPLE"

        if source_state == MemoryState.CONFLICTED:
            strategy = TeachBackInteractionType.RESOLVE_CONTRADICTION
            reason_code = "MEMORY_CONFLICTED"
        elif source_state == MemoryState.MISCONCEIVED:
            strategy = TeachBackInteractionType.CORRECT_ARIEL
            reason_code = "MEMORY_MISCONCEIVED"
        elif source_state in {MemoryState.FRAGILE, MemoryState.FORGOTTEN}:
            strategy = TeachBackInteractionType.RETEACH_AFTER_DELAY
            reason_code = "MEMORY_NEEDS_RETEACH"
        elif "term" in normalized_concept or "definition" in normalized_concept:
            strategy = TeachBackInteractionType.CLARIFY_TERM
            reason_code = "TERM_NEEDS_CLARIFICATION"
        elif "step" in normalized_concept or "process" in normalized_concept:
            strategy = TeachBackInteractionType.EXPLAIN_STEP
            reason_code = "STEPWISE_EXPLANATION_REQUESTED"
        elif "what if" in normalized_concept or "cause" in normalized_concept:
            strategy = TeachBackInteractionType.WHAT_IF
            reason_code = "CAUSAL_VARIATION_REQUESTED"
        elif normalized_artefact_type in {"diagram", "concept_map", "whiteboard_snapshot"}:
            strategy = TeachBackInteractionType.LABEL_DIAGRAM if input_provenance == TeachingInputProvenance.STUDY_LAB_ARTEFACT else TeachBackInteractionType.DRAW_OR_DIAGRAM
            reason_code = "VISUAL_TEACHING_CONTEXT"
        elif related_memory_count >= 2:
            strategy = TeachBackInteractionType.CONNECT_IDEAS
            reason_code = "MULTIPLE_RELATED_MEMORIES"
        elif normalized_concept and "compare" in normalized_concept:
            strategy = TeachBackInteractionType.COMPARE_CASES
            reason_code = "COMPARISON_REQUESTED"
        elif prior_strategy_codes and prior_strategy_codes[-1] == TeachBackInteractionType.NEW_EXAMPLE:
            strategy = TeachBackInteractionType.COMPARE_CASES
            reason_code = "PRIOR_STRATEGY_REPEATED"

        template = ArielTeachBackTemplateRegistry.get(strategy)
        intensity = ArielProductiveStrugglePolicy.resolve_intensity(
            source_memory_state=source_state,
            source_memory_confidence=source_confidence,
            memory_age_days=memory_age_days,
            recent_interactions=recent_interactions,
            unresolved_interactions=unresolved_interactions,
        )

        requires_artefact = transformation["requires_transformation"]
        required_artefact_type = ""
        if strategy == TeachBackInteractionType.DRAW_OR_DIAGRAM:
            requires_artefact = True
            required_artefact_type = "diagram"
        elif strategy == TeachBackInteractionType.LABEL_DIAGRAM:
            requires_artefact = True
            required_artefact_type = normalized_artefact_type or "diagram"
        elif strategy == TeachBackInteractionType.COMPARE_CASES:
            requires_artefact = True
            required_artefact_type = "comparison_table"
        elif strategy == TeachBackInteractionType.CONNECT_IDEAS:
            requires_artefact = True
            required_artefact_type = "concept_map"

        return {
            "strategy": strategy.value if hasattr(strategy, "value") else str(strategy),
            "reason_code": reason_code if reason_code else transformation["reason_code"],
            "source_memory_id": str(source_memory_unit.id) if source_memory_unit else None,
            "intensity": intensity.value if hasattr(intensity, "value") else intensity,
            "requires_artefact": requires_artefact,
            "required_artefact_type": required_artefact_type,
            "prompt_template_key": template["template_key"],
            "prompt_template_version": template["template_version"],
            "prompt_text": template["prompt_text"],
            "transformation_required": transformation["requires_transformation"],
            "transformation_type": transformation["transformation_type"],
            "input_provenance": input_provenance,
        }


class ResolveDelayedReteachingService:
    """Return whether Ariel should request reteaching for a memory unit."""

    @staticmethod
    def execute(*, source_memory_unit: ArielKnowledgeUnit, memory_age_days: int | None = None, recent_interactions: int = 0) -> dict:
        eligible = source_memory_unit.memory_state in {MemoryState.FRAGILE, MemoryState.FORGOTTEN}
        urgent = source_memory_unit.memory_state == MemoryState.FORGOTTEN or recent_interactions >= 3
        if memory_age_days is not None and memory_age_days < 7:
            eligible = False
            urgent = False
        return {
            "status": "URGENT_RETEACH" if urgent and eligible else "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
            "memory_id": str(source_memory_unit.id),
            "reason_code": source_memory_unit.memory_state,
        }


class ResolveArielMisunderstandingService:
    """Return a safe explanation of Ariel's current misunderstanding state."""

    @staticmethod
    def execute(*, source_memory_unit: ArielKnowledgeUnit) -> dict:
        if source_memory_unit.memory_state == MemoryState.MISCONCEIVED:
            summary = "Ariel retains a misconception and needs learner correction."
            code = "MISCONCEIVED"
        elif source_memory_unit.memory_state == MemoryState.CONFLICTED:
            summary = "Ariel has conflicting memories and needs the learner to resolve the contradiction."
            code = "CONFLICTED"
        elif source_memory_unit.memory_state == MemoryState.FRAGILE:
            summary = "Ariel remembers this weakly and may need reteaching."
            code = "FRAGILE"
        elif source_memory_unit.memory_state == MemoryState.FORGOTTEN:
            summary = "Ariel no longer remembers this clearly."
            code = "FORGOTTEN"
        else:
            summary = "Ariel is uncertain about this memory."
            code = "LOW_CONFIDENCE"
        return {
            "status": code,
            "memory_id": str(source_memory_unit.id),
            "summary": summary,
        }


def _normalize_study_lab_artefact_kind(artefact_type: str) -> str:
    mapping = {
        "DIAGRAM_ARTEFACT": "diagram",
        "CONCEPT_MAP": "concept_map",
        "WHITEBOARD_SNAPSHOT": "whiteboard_snapshot",
        "COMPARISON_TABLE": "comparison_table",
        "GRAPH_ARTEFACT": "graph",
        "FORMULA_SHEET": "formula_sheet",
        "FLASHCARD_SET": "flashcard_set",
        "FLASHCARD": "flashcard",
        "SCRATCHPAD_ARTEFACT": "scratchpad",
        "CODE_ARTEFACT": "code",
        "TEXT_NOTE": "text_note",
        "REVISION_SUMMARY": "revision_summary",
        "RESOURCE_EXCERPT": "resource_excerpt",
        "LEARNER_EXPLANATION": "learner_explanation",
        "ARIEL_TEACHING_ARTEFACT": "ariel_teaching_artefact",
    }
    return mapping.get(str(artefact_type), str(artefact_type).lower())


def _derive_study_lab_authorship(artefact) -> str:
    native_payload = artefact.native_payload if isinstance(artefact.native_payload, dict) else {}
    authorship = native_payload.get("authorship")
    if authorship:
        return str(authorship)
    if getattr(artefact, "creation_source", "") in {"REFERENCED", "IMPORTED", "EXPORTED", "TRANSFORMED"}:
        return "SOURCE_REFERENCED"
    return "LEARNER_AUTHORED"


class CreateDelayedReteachingInteractionService:
    """Create a deterministic reteach teach-back interaction for a fragile or forgotten memory."""

    @staticmethod
    @transaction.atomic
    def execute(
        *,
        identity: ArielIdentity,
        teaching_session: ArielTeachingSession,
        learner_id,
        source_memory_unit_id,
        interaction: ArielTeachBackInteraction | None = None,
        workspace_id=None,
        auto_present=True,
    ):
        if identity.learner_id != learner_id or teaching_session.learner_id != learner_id or teaching_session.identity_id != identity.id:
            raise ValidationError("Only the owning learner can request reteaching.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")

        source_memory_unit = ArielKnowledgeUnit.objects.filter(
            pk=source_memory_unit_id,
            identity=identity,
            learner_id=learner_id,
        ).first()
        if source_memory_unit is None:
            raise ValidationError("Source memory is not available.", code="ARIEL_TEACH_BACK_NOT_FOUND")

        eligibility = ResolveDelayedReteachingService.execute(source_memory_unit=source_memory_unit)
        if eligibility["status"] == "NOT_ELIGIBLE":
            raise ValidationError("Memory is not eligible for reteaching.", code="ARIEL_MEMORY_NOT_ELIGIBLE_FOR_RETEACH")

        if interaction is None:
            interaction = ArielTeachBackInteraction.objects.create(
                identity=identity,
                teaching_session=teaching_session,
                learner_id=learner_id,
                workspace_id=workspace_id,
                learning_journey_id=teaching_session.learning_journey_id,
                subject_id=teaching_session.subject_id,
                concept_reference=teaching_session.concept_reference,
                source_memory_unit=source_memory_unit,
                interaction_type=TeachBackInteractionType.RETEACH_AFTER_DELAY,
                status=TeachBackInteractionStatus.PROPOSED,
                strategy_reason_code=eligibility["reason_code"],
                intensity=TeachBackIntensity.STANDARD if eligibility["status"] == "ELIGIBLE" else TeachBackIntensity.DEEP,
                prompt_template_key=ArielTeachBackTemplateRegistry.get(TeachBackInteractionType.RETEACH_AFTER_DELAY)["template_key"],
                prompt_template_version=ArielTeachBackTemplateRegistry.get(TeachBackInteractionType.RETEACH_AFTER_DELAY)["template_version"],
                input_provenance=TeachingInputProvenance.UNKNOWN,
                requires_artefact=False,
                required_artefact_type="",
            )
        else:
            if (
                interaction.identity_id != identity.id
                or interaction.teaching_session_id != teaching_session.id
                or interaction.learner_id != learner_id
                or interaction.source_memory_unit_id != source_memory_unit.id
            ):
                raise ValidationError("Teach-back interaction does not match the requested reteach.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")
            interaction.strategy_reason_code = eligibility["reason_code"]
            interaction.intensity = TeachBackIntensity.STANDARD if eligibility["status"] == "ELIGIBLE" else TeachBackIntensity.DEEP
            interaction.interaction_type = TeachBackInteractionType.RETEACH_AFTER_DELAY
            interaction.prompt_template_key = ArielTeachBackTemplateRegistry.get(TeachBackInteractionType.RETEACH_AFTER_DELAY)["template_key"]
            interaction.prompt_template_version = ArielTeachBackTemplateRegistry.get(TeachBackInteractionType.RETEACH_AFTER_DELAY)["template_version"]
            interaction.input_provenance = TeachingInputProvenance.UNKNOWN
            interaction.requires_artefact = False
            interaction.required_artefact_type = ""
            if interaction.status == TeachBackInteractionStatus.PROPOSED:
                interaction.present()
            interaction.save()

        if auto_present:
            interaction.present()
            interaction.save()

        return interaction, eligibility


class TeachArielFromArtefactService:
    """Teach Ariel from a learner-approved Study Lab artefact reference."""

    @staticmethod
    @transaction.atomic
    def execute(
        *,
        identity: ArielIdentity,
        teaching_session: ArielTeachingSession,
        learner_id,
        workspace_id,
        artefact_id,
        learner_explanation: str,
        concept_reference: str = "",
        source_memory_unit_id=None,
        create_memory: bool = False,
        auto_present: bool = True,
    ):
        if not learner_explanation.strip():
            raise ValidationError("Learner explanation is required.", code="ARIEL_ARTEFACT_TRANSFORMATION_REQUIRED")
        if identity.learner_id != learner_id or teaching_session.learner_id != learner_id or teaching_session.identity_id != identity.id:
            raise ValidationError("Only the owning learner can teach Ariel from artefact.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")

        from apps.study_lab.domain.enums import StudyArtefactCompatibilityStatus, StudyArtefactLifecycle, StudyArtefactOrigin
        from apps.study_lab.domain.models import StudyArtefact, StudyWorkspace
        from apps.study_lab.application.interoperability_services import ResolveArtefactCompatibilityService

        workspace = StudyWorkspace.objects.filter(pk=workspace_id, learner_id=learner_id).first()
        if workspace is None:
            raise ValidationError("Workspace access denied.", code="ARIEL_ARTEFACT_ACCESS_DENIED")
        artefact = StudyArtefact.objects.filter(pk=artefact_id, workspace_id=workspace_id, learner_id=learner_id).first()
        if artefact is None:
            raise ValidationError("Artefact access denied.", code="ARIEL_ARTEFACT_ACCESS_DENIED")
        if artefact.lifecycle == StudyArtefactLifecycle.ARCHIVED:
            raise ValidationError("Artefact is archived.", code="ARIEL_ARTEFACT_NOT_COMPATIBLE")
        if workspace.tenant_id != artefact.tenant_id and (workspace.tenant_id is not None or artefact.tenant_id is not None):
            raise ValidationError("Artefact tenant mismatch.", code="ARIEL_ARTEFACT_ACCESS_DENIED")

        compatibility = ResolveArtefactCompatibilityService.execute(
            workspace_id,
            learner_id,
            artefact_type=artefact.artefact_type,
            schema_version=artefact.schema_version,
            provider_context=artefact.provider_context,
            artefact_id=artefact.id,
        )
        if compatibility["status"] in {
            StudyArtefactCompatibilityStatus.UNSUPPORTED_TYPE,
            StudyArtefactCompatibilityStatus.UNSUPPORTED_SCHEMA,
            StudyArtefactCompatibilityStatus.ACCESS_DENIED,
            StudyArtefactCompatibilityStatus.ARTEFACT_ARCHIVED,
            StudyArtefactCompatibilityStatus.PROVIDER_UNAVAILABLE,
            StudyArtefactCompatibilityStatus.SHARING_NOT_ALLOWED,
        }:
            raise ValidationError("Artefact is not compatible for teaching.", code="ARIEL_ARTEFACT_NOT_COMPATIBLE")

        authorship = _derive_study_lab_authorship(artefact)
        normalized_kind = _normalize_study_lab_artefact_kind(artefact.artefact_type)
        decision = ResolveArielTeachBackStrategyService.execute(
            source_memory_unit=ArielKnowledgeUnit.objects.filter(pk=source_memory_unit_id, identity=identity, learner_id=learner_id).first() if source_memory_unit_id else None,
            concept_reference=concept_reference or artefact.title or artefact.summary or "",
            input_provenance=TeachingInputProvenance.STUDY_LAB_ARTEFACT,
            learner_approved_artefact_type=normalized_kind,
            authorship_classification=authorship,
            related_memory_count=0,
            recent_interactions=0,
            unresolved_interactions=0,
            prior_strategy_codes=[],
            memory_age_days=None,
        )

        interaction = ArielTeachBackInteraction.objects.create(
            identity=identity,
            teaching_session=teaching_session,
            learner_id=learner_id,
            workspace_id=workspace_id,
            learning_journey_id=teaching_session.learning_journey_id,
            subject_id=teaching_session.subject_id,
            concept_reference=concept_reference or artefact.title or artefact.summary or "",
            source_memory_unit=ArielKnowledgeUnit.objects.filter(pk=source_memory_unit_id, identity=identity, learner_id=learner_id).first() if source_memory_unit_id else None,
            interaction_type=decision["strategy"],
            status=TeachBackInteractionStatus.ACTIVE,
            strategy_reason_code=decision["reason_code"],
            intensity=decision["intensity"],
            prompt_template_key=decision["prompt_template_key"],
            prompt_template_version=decision["prompt_template_version"],
            input_provenance=TeachingInputProvenance.STUDY_LAB_ARTEFACT,
            requires_artefact=decision["requires_artefact"],
            required_artefact_type=decision["required_artefact_type"],
            presented_at=timezone.now(),
        )

        turn = ArielTeachingService.add_teaching_turn(
            session=teaching_session,
            actor=TeachingTurnActor.LEARNER,
            content=learner_explanation.strip(),
            disposition=TeachingTurnDisposition.TEACHING,
        )
        turn.resulting_memory_effect = {
            "artefact_id": str(artefact.id),
            "artefact_type": artefact.artefact_type,
            "authorship_classification": authorship,
            "creation_source": artefact.creation_source,
            "compatibility_status": compatibility["status"],
            "transformation_type": decision["transformation_type"],
        }
        turn.save(update_fields=["resulting_memory_effect"])

        interaction.learner_response_turn = turn
        interaction.responded_at = timezone.now()
        interaction.resolved_at = interaction.responded_at
        interaction.status = TeachBackInteractionStatus.RESOLVED
        interaction.version += 1
        interaction.save()

        knowledge = None
        if create_memory:
            knowledge = ArielTeachingService.create_knowledge_from_teaching(
                session=teaching_session,
                teaching_turn=turn,
                normalized_statement=learner_explanation.strip(),
                confidence=0.5,
            )

        return interaction, turn, knowledge, decision, artefact


class CorrectArielMisunderstandingService:
    """Create a correction turn for a misunderstood Ariel memory."""

    @staticmethod
    @transaction.atomic
    def execute(
        *,
        identity: ArielIdentity,
        teaching_session: ArielTeachingSession,
        learner_id,
        source_memory_unit_id,
        correction_text: str,
        concept_reference: str = "",
        create_memory: bool = True,
        interaction: ArielTeachBackInteraction | None = None,
    ):
        if not correction_text.strip():
            raise ValidationError("Correction text is required.", code="ARIEL_TEACH_BACK_TRANSFORMATION_REQUIRED")
        if identity.learner_id != learner_id or teaching_session.learner_id != learner_id or teaching_session.identity_id != identity.id:
            raise ValidationError("Only the owning learner can correct Ariel.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")

        source_memory_unit = ArielKnowledgeUnit.objects.filter(pk=source_memory_unit_id, identity=identity, learner_id=learner_id).first()
        if source_memory_unit is None:
            raise ValidationError("Source memory is not available.", code="ARIEL_TEACH_BACK_NOT_FOUND")

        misunderstanding = ResolveArielMisunderstandingService.execute(source_memory_unit=source_memory_unit)
        template_type = TeachBackInteractionType.CORRECT_ARIEL if misunderstanding["status"] == "MISCONCEIVED" else TeachBackInteractionType.RESOLVE_CONTRADICTION
        template = ArielTeachBackTemplateRegistry.get(template_type)
        if interaction is None:
            interaction = ArielTeachBackInteraction.objects.create(
                identity=identity,
                teaching_session=teaching_session,
                learner_id=learner_id,
                workspace_id=None,
                learning_journey_id=teaching_session.learning_journey_id,
                subject_id=teaching_session.subject_id,
                concept_reference=concept_reference or source_memory_unit.concept_reference,
                source_memory_unit=source_memory_unit,
                interaction_type=template_type,
                status=TeachBackInteractionStatus.ACTIVE,
                strategy_reason_code=misunderstanding["status"],
                intensity=TeachBackIntensity.DEEP if misunderstanding["status"] in {"MISCONCEIVED", "CONFLICTED"} else TeachBackIntensity.STANDARD,
                prompt_template_key=template["template_key"],
                prompt_template_version=template["template_version"],
                input_provenance=TeachingInputProvenance.DIRECT_TYPED_EXPLANATION,
                requires_artefact=False,
                required_artefact_type="",
                presented_at=timezone.now(),
            )
        else:
            if (
                interaction.identity_id != identity.id
                or interaction.teaching_session_id != teaching_session.id
                or interaction.learner_id != learner_id
                or interaction.source_memory_unit_id != source_memory_unit.id
            ):
                raise ValidationError("Teach-back interaction does not match the requested correction.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")
            interaction.concept_reference = concept_reference or source_memory_unit.concept_reference
            interaction.source_memory_unit = source_memory_unit
            interaction.interaction_type = template_type
            interaction.strategy_reason_code = misunderstanding["status"]
            interaction.intensity = TeachBackIntensity.DEEP if misunderstanding["status"] in {"MISCONCEIVED", "CONFLICTED"} else TeachBackIntensity.STANDARD
            interaction.prompt_template_key = template["template_key"]
            interaction.prompt_template_version = template["template_version"]
            interaction.input_provenance = TeachingInputProvenance.DIRECT_TYPED_EXPLANATION
            interaction.requires_artefact = False
            interaction.required_artefact_type = ""
            if interaction.status == TeachBackInteractionStatus.PROPOSED:
                interaction.presented_at = timezone.now()
                interaction.status = TeachBackInteractionStatus.ACTIVE
                interaction.version += 1
                interaction.save()

        turn = ArielTeachingService.add_teaching_turn(
            session=teaching_session,
            actor=TeachingTurnActor.LEARNER,
            content=correction_text.strip(),
            disposition=TeachingTurnDisposition.CORRECTION,
        )
        interaction.learner_response_turn = turn
        interaction.responded_at = timezone.now()
        interaction.resolved_at = interaction.responded_at
        interaction.status = TeachBackInteractionStatus.RESOLVED
        interaction.version += 1
        interaction.save()

        knowledge = None
        if create_memory:
            knowledge = ArielTeachingService.correct_knowledge(
                old_knowledge=source_memory_unit,
                teaching_turn=turn,
                new_normalized_statement=correction_text.strip(),
                correction_reason=misunderstanding["summary"],
            )

        return interaction, turn, knowledge, misunderstanding


class StartArielTeachBackInteractionService:
    """Create a teach-back interaction from Ariel-owned state."""

    @staticmethod
    @transaction.atomic
    def execute(
        *,
        identity: ArielIdentity,
        teaching_session: ArielTeachingSession,
        learner_id,
        source_memory_unit_id=None,
        concept_reference="",
        input_provenance=TeachingInputProvenance.UNKNOWN,
        learner_approved_artefact_type="",
        authorship_classification="",
        related_memory_count=0,
        recent_interactions=0,
        unresolved_interactions=0,
        prior_strategy_codes=None,
        memory_age_days=None,
        workspace_id=None,
        auto_present=True,
    ):
        if identity.learner_id != learner_id:
            raise ValidationError("Only the owning learner can start teach-back.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")
        if teaching_session.identity_id != identity.id or teaching_session.learner_id != learner_id:
            raise ValidationError("Teach-back session must belong to the learner.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")

        source_memory_unit = None
        if source_memory_unit_id:
            source_memory_unit = ArielKnowledgeUnit.objects.filter(pk=source_memory_unit_id, identity=identity, learner_id=learner_id).first()
            if source_memory_unit is None:
                raise ValidationError("Source memory is not available.", code="ARIEL_TEACH_BACK_NOT_FOUND")

        decision = ResolveArielTeachBackStrategyService.execute(
            source_memory_unit=source_memory_unit,
            concept_reference=concept_reference,
            input_provenance=input_provenance,
            learner_approved_artefact_type=learner_approved_artefact_type,
            authorship_classification=authorship_classification,
            related_memory_count=related_memory_count,
            recent_interactions=recent_interactions,
            unresolved_interactions=unresolved_interactions,
            prior_strategy_codes=prior_strategy_codes,
            memory_age_days=memory_age_days,
        )

        interaction = ArielTeachBackInteraction.objects.create(
            identity=identity,
            teaching_session=teaching_session,
            learner_id=learner_id,
            workspace_id=workspace_id,
            learning_journey_id=teaching_session.learning_journey_id,
            subject_id=teaching_session.subject_id,
            concept_reference=concept_reference or teaching_session.concept_reference,
            source_memory_unit=source_memory_unit,
            interaction_type=decision["strategy"],
            status=TeachBackInteractionStatus.PROPOSED,
            strategy_reason_code=decision["reason_code"],
            intensity=decision["intensity"],
            prompt_template_key=decision["prompt_template_key"],
            prompt_template_version=decision["prompt_template_version"],
            input_provenance=input_provenance,
            requires_artefact=decision["requires_artefact"],
            required_artefact_type=decision["required_artefact_type"],
        )

        if auto_present:
            interaction.present()
            if decision["requires_artefact"]:
                interaction.await_artefact()
            interaction.save()

        return interaction, decision


class PresentArielTeachBackInteractionService:
    """Present a proposed teach-back interaction."""

    @staticmethod
    @transaction.atomic
    def execute(*, interaction: ArielTeachBackInteraction, learner_id):
        if interaction.learner_id != learner_id:
            raise ValidationError("Only the owning learner can present teach-back.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")
        if interaction.status == TeachBackInteractionStatus.ACTIVE:
            return interaction
        if interaction.status != TeachBackInteractionStatus.PROPOSED:
            raise ValidationError("Teach-back interaction cannot be presented.", code="ARIEL_TEACH_BACK_INVALID_TRANSITION")
        interaction.present()
        interaction.save()
        return interaction


class RecordTeachBackResponseService:
    """Record a learner response to a teach-back interaction."""

    @staticmethod
    @transaction.atomic
    def execute(*, interaction: ArielTeachBackInteraction, learner_id, content: str, disposition=TeachingTurnDisposition.TEACHING, create_memory: bool = False):
        if interaction.learner_id != learner_id:
            raise ValidationError("Only the owning learner can respond.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")
        if interaction.status not in {TeachBackInteractionStatus.ACTIVE, TeachBackInteractionStatus.AWAITING_LEARNER, TeachBackInteractionStatus.AWAITING_ARTEFACT}:
            raise ValidationError("Teach-back interaction is not awaiting a response.", code="ARIEL_TEACH_BACK_INVALID_TRANSITION")

        turn = ArielTeachingService.add_teaching_turn(
            session=interaction.teaching_session,
            actor=TeachingTurnActor.LEARNER,
            content=content,
            disposition=disposition,
        )

        interaction.learner_response_turn = turn
        interaction.responded_at = timezone.now()
        interaction.resolve(when=interaction.responded_at)
        interaction.save()

        knowledge = None
        if create_memory:
            knowledge = ArielTeachingService.create_knowledge_from_teaching(
                session=interaction.teaching_session,
                teaching_turn=turn,
                normalized_statement=content,
                confidence=0.5,
            )

        return interaction, turn, knowledge


class SkipArielTeachBackInteractionService:
    """Skip a teach-back interaction without changing Ariel memory."""

    @staticmethod
    @transaction.atomic
    def execute(*, interaction: ArielTeachBackInteraction, learner_id):
        if interaction.learner_id != learner_id:
            raise ValidationError("Only the owning learner can skip teach-back.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")
        if interaction.status in {
            TeachBackInteractionStatus.RESOLVED,
            TeachBackInteractionStatus.EXPIRED,
            TeachBackInteractionStatus.CANCELLED,
        }:
            raise ValidationError("Teach-back interaction cannot be skipped.", code="ARIEL_TEACH_BACK_INVALID_TRANSITION")
        if interaction.skip():
            interaction.save()
        return interaction


class CancelArielTeachBackInteractionService:
    """Cancel a teach-back interaction."""

    @staticmethod
    @transaction.atomic
    def execute(*, interaction: ArielTeachBackInteraction, learner_id):
        if interaction.learner_id != learner_id:
            raise ValidationError("Only the owning learner can cancel teach-back.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")
        if interaction.status in {
            TeachBackInteractionStatus.RESOLVED,
            TeachBackInteractionStatus.SKIPPED,
            TeachBackInteractionStatus.EXPIRED,
        }:
            raise ValidationError("Teach-back interaction cannot be cancelled.", code="ARIEL_TEACH_BACK_INVALID_TRANSITION")
        if interaction.cancel():
            interaction.save()
        return interaction


class ListArielTeachBackStrategiesQuery:
    """Learner-safe catalog of active teach-back strategies."""

    @staticmethod
    def execute():
        return ArielTeachBackTemplateRegistry.list()


class GetArielTeachBackInteractionQuery:
    """Fetch a learner-owned teach-back interaction."""

    @staticmethod
    def execute(*, interaction: ArielTeachBackInteraction, learner_id):
        if interaction.learner_id != learner_id:
            raise ValidationError("Only the owning learner can view teach-back.", code="ARIEL_TEACH_BACK_ACCESS_DENIED")
        return interaction
