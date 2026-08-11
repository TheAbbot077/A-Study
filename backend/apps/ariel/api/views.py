from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.ariel.api.serializers import (
    ArielIdentitySerializer,
    ArielKnowledgeUnitSerializer,
    ArielMemoryRecordSerializer,
    ArielTeachBackInteractionSerializer,
    ArielTeachingSessionSerializer,
    ArielTeachingTurnSerializer,
)
from apps.ariel.application.services import (
    ArielAuthorizationService,
    CancelArielTeachBackInteractionService,
    CorrectArielMisunderstandingService,
    CreateDelayedReteachingInteractionService,
    GetArielTeachBackInteractionQuery,
    ArielIdentityService,
    ListArielTeachBackStrategiesQuery,
    ResolveArielMisunderstandingService,
    ArielTeachingService,
    RecordTeachBackResponseService,
    ConstitutionEnforcementService,
    PresentArielTeachBackInteractionService,
    SkipArielTeachBackInteractionService,
    StartArielTeachBackInteractionService,
    TeachArielFromArtefactService,
)
from apps.ariel.domain.models import (
    ArielCapability,
    ArielIdentity,
    ArielIdentityStatus,
    ArielKnowledgeUnit,
    ArielMemoryRecord,
    ArielTeachBackInteraction,
    TeachingInputProvenance,
    ArielTeachingSession,
    ArielTeachingTurn,
    TeachingTurnDisposition,
    KnowledgeProvenance,
    MemoryState,
    TeachingTurnActor,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_ariel_identity(request):
    """Create a new Ariel identity for the authenticated learner."""
    identity = ArielIdentityService.create_identity(
        learner_id=request.user.id,
        institution_id=request.data.get("institution_id"),
        display_name=request.data.get("display_name", "Ariel"),
    )
    serializer = ArielIdentitySerializer(identity)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_ariel_identity(request, identity_id):
    """Get Ariel identity details."""
    identity = ArielIdentity.objects.filter(pk=identity_id).first()
    if not identity:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    serializer = ArielIdentitySerializer(identity)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def activate_ariel(request, identity_id):
    """Activate an Ariel identity."""
    identity = ArielIdentity.objects.filter(pk=identity_id).first()
    if not identity:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    identity = ArielIdentityService.activate_identity(identity)
    serializer = ArielIdentitySerializer(identity)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def suspend_ariel(request, identity_id):
    """Suspend an Ariel identity."""
    identity = ArielIdentity.objects.filter(pk=identity_id).first()
    if not identity:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.can_suspend(request.user.id, identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    identity = ArielIdentityService.suspend_identity(identity)
    serializer = ArielIdentitySerializer(identity)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reset_ariel(request, identity_id):
    """Reset Ariel memory while preserving audit history."""
    identity = ArielIdentity.objects.filter(pk=identity_id).first()
    if not identity:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.can_reset(request.user.id, identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    identity = ArielIdentityService.reset_identity(identity)
    serializer = ArielIdentitySerializer(identity)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_teaching_session(request, identity_id):
    """Start a new teaching session."""
    identity = ArielIdentity.objects.filter(pk=identity_id).first()
    if not identity:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    session = ArielTeachingService.start_teaching_session(
        identity=identity,
        learner_id=request.user.id,
        learning_journey_id=request.data.get("learning_journey_id"),
        subject_id=request.data.get("subject_id"),
        concept_reference=request.data.get("concept_reference", ""),
    )
    serializer = ArielTeachingSessionSerializer(session)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_teaching_sessions(request, identity_id):
    """List teaching sessions for an Ariel identity."""
    if not ArielAuthorizationService.can_view_memory(request.user.id, identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    sessions = ArielTeachingSession.objects.filter(identity_id=identity_id).order_by("-created_at")
    serializer = ArielTeachingSessionSerializer(sessions, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_teaching_turn(request, session_id):
    """Add a teaching turn to a session."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    turn = ArielTeachingService.add_teaching_turn(
        session=session,
        actor=request.data.get("actor", TeachingTurnActor.LEARNER),
        content=request.data["content"],
        disposition=request.data.get("disposition", TeachingTurnDisposition.CONVERSATION),
    )
    serializer = ArielTeachingTurnSerializer(turn)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_teaching_turns(request, session_id):
    """List teaching turns for a session."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.can_view_memory(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    turns = session.turns.all()
    serializer = ArielTeachingTurnSerializer(turns, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_knowledge(request, session_id):
    """Create knowledge from a teaching turn. Only learner teaching allowed."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    teaching_turn = ArielTeachingTurn.objects.filter(pk=request.data["teaching_turn_id"]).first()
    if not teaching_turn:
        return Response({"detail": "Teaching turn not found"}, status=status.HTTP_404_NOT_FOUND)

    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=session,
        teaching_turn=teaching_turn,
        normalized_statement=request.data["normalized_statement"],
        confidence=float(request.data.get("confidence", 0.5)),
        subject_id=request.data.get("subject_id"),
        concept_reference=request.data.get("concept_reference", ""),
    )
    serializer = ArielKnowledgeUnitSerializer(knowledge)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_knowledge(request, identity_id):
    """List knowledge units for an Ariel identity."""
    if not ArielAuthorizationService.can_view_memory(request.user.id, identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    knowledge = ArielKnowledgeUnit.objects.filter(identity_id=identity_id).order_by("-created_at")
    serializer = ArielKnowledgeUnitSerializer(knowledge, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reinforce_knowledge(request, knowledge_id):
    """Reinforce existing knowledge."""
    knowledge = ArielKnowledgeUnit.objects.filter(pk=knowledge_id).first()
    if not knowledge:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.can_correct_memory(request.user.id, knowledge.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    teaching_turn = ArielTeachingTurn.objects.filter(pk=request.data["teaching_turn_id"]).first()
    if not teaching_turn:
        return Response({"detail": "Teaching turn not found"}, status=status.HTTP_404_NOT_FOUND)

    knowledge = ArielTeachingService.reinforce_knowledge(
        knowledge=knowledge,
        teaching_turn=teaching_turn,
        new_confidence=request.data.get("new_confidence"),
    )
    serializer = ArielKnowledgeUnitSerializer(knowledge)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def correct_knowledge(request, knowledge_id):
    """Correct existing knowledge, preserving history."""
    knowledge = ArielKnowledgeUnit.objects.filter(pk=knowledge_id).first()
    if not knowledge:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.can_correct_memory(request.user.id, knowledge.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    teaching_turn = ArielTeachingTurn.objects.filter(pk=request.data["teaching_turn_id"]).first()
    if not teaching_turn:
        return Response({"detail": "Teaching turn not found"}, status=status.HTTP_404_NOT_FOUND)

    new_knowledge = ArielTeachingService.correct_knowledge(
        old_knowledge=knowledge,
        teaching_turn=teaching_turn,
        new_normalized_statement=request.data["new_normalized_statement"],
        correction_reason=request.data.get("correction_reason", ""),
        confidence=float(request.data.get("confidence", 0.5)),
    )
    serializer = ArielKnowledgeUnitSerializer(new_knowledge)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def forget_knowledge(request, knowledge_id):
    """Initiate forgetting for a knowledge unit."""
    knowledge = ArielKnowledgeUnit.objects.filter(pk=knowledge_id).first()
    if not knowledge:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.can_forget_memory(request.user.id, knowledge.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    knowledge = ArielTeachingService.forget_knowledge(
        knowledge=knowledge,
        reason=request.data.get("reason", "LEARNER_REQUEST"),
    )
    serializer = ArielKnowledgeUnitSerializer(knowledge)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def retract_knowledge(request, knowledge_id):
    """Retract a knowledge unit."""
    knowledge = ArielKnowledgeUnit.objects.filter(pk=knowledge_id).first()
    if not knowledge:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.can_correct_memory(request.user.id, knowledge.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    knowledge = ArielTeachingService.retract_knowledge(knowledge)
    serializer = ArielKnowledgeUnitSerializer(knowledge)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_memory_records(request, identity_id):
    """List memory records (provenance/history) for an Ariel identity."""
    if not ArielAuthorizationService.can_view_memory(request.user.id, identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    records = ArielMemoryRecord.objects.filter(identity_id=identity_id).order_by("-created_at")
    serializer = ArielMemoryRecordSerializer(records, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_memory(request, identity_id):
    """Export Ariel memory metadata."""
    if not ArielAuthorizationService.can_export(request.user.id, identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    knowledge = ArielKnowledgeUnit.objects.filter(identity_id=identity_id).values(
        "id", "normalized_statement", "confidence", "memory_state", "provenance",
        "concept_reference", "created_at", "updated_at",
    )
    records = ArielMemoryRecord.objects.filter(identity_id=identity_id).values(
        "id", "knowledge_unit_id", "previous_state", "new_state", "transition_reason", "created_at",
    )
    return Response({
        "knowledge_units": list(knowledge),
        "memory_records": list(records),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_teach_back_strategies(request):
    """List learner-safe teach-back strategies."""
    return Response(ListArielTeachBackStrategiesQuery.execute())


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_teach_back(request, session_id):
    """Start a teach-back interaction for a learner-owned teaching session."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    interaction, decision = StartArielTeachBackInteractionService.execute(
        identity=session.identity,
        teaching_session=session,
        learner_id=request.user.id,
        source_memory_unit_id=request.data.get("source_memory_unit_id"),
        concept_reference=request.data.get("concept_reference", ""),
        input_provenance=request.data.get("input_provenance", TeachingInputProvenance.UNKNOWN),
        learner_approved_artefact_type=request.data.get("learner_approved_artefact_type", ""),
        authorship_classification=request.data.get("authorship_classification", ""),
        related_memory_count=int(request.data.get("related_memory_count", 0) or 0),
        recent_interactions=int(request.data.get("recent_interactions", 0) or 0),
        unresolved_interactions=int(request.data.get("unresolved_interactions", 0) or 0),
        prior_strategy_codes=request.data.get("prior_strategy_codes") or [],
        memory_age_days=(
            int(request.data["memory_age_days"]) if request.data.get("memory_age_days") not in {None, ""} else None
        ),
        workspace_id=request.data.get("workspace_id"),
        auto_present=bool(request.data.get("auto_present", True)),
    )
    serializer = ArielTeachBackInteractionSerializer(interaction)
    payload = serializer.data
    payload["strategy"] = decision["strategy"]
    payload["prompt_text"] = decision["prompt_text"]
    payload["transformation_required"] = decision["transformation_required"]
    payload["transformation_type"] = decision["transformation_type"]
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def present_teach_back_interaction(request, session_id, interaction_id):
    """Present a proposed teach-back interaction."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    interaction = ArielTeachBackInteraction.objects.filter(pk=interaction_id, teaching_session_id=session_id).first()
    if not interaction:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    interaction = PresentArielTeachBackInteractionService.execute(interaction=interaction, learner_id=request.user.id)
    serializer = ArielTeachBackInteractionSerializer(interaction)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_teach_back_interaction(request, session_id, interaction_id):
    """Get a learner-owned teach-back interaction."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    interaction = ArielTeachBackInteraction.objects.filter(pk=interaction_id, teaching_session_id=session_id).first()
    if not interaction:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    interaction = GetArielTeachBackInteractionQuery.execute(interaction=interaction, learner_id=request.user.id)
    serializer = ArielTeachBackInteractionSerializer(interaction)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def respond_teach_back_interaction(request, session_id, interaction_id):
    """Record a learner response and resolve a teach-back interaction."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    interaction = ArielTeachBackInteraction.objects.filter(pk=interaction_id, teaching_session_id=session_id).first()
    if not interaction:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    interaction, turn, knowledge = RecordTeachBackResponseService.execute(
        interaction=interaction,
        learner_id=request.user.id,
        content=request.data["content"],
        disposition=request.data.get("disposition", TeachingTurnDisposition.TEACHING),
        create_memory=bool(request.data.get("create_memory", False)),
    )
    serializer = ArielTeachBackInteractionSerializer(interaction)
    payload = serializer.data
    payload["learner_response_turn_id"] = str(turn.id)
    if knowledge is not None:
        payload["knowledge_unit_id"] = str(knowledge.id)
    return Response(payload)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def request_teach_back_artefact(request, session_id, interaction_id):
    """Move a teach-back interaction into awaiting-artefact state."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    interaction = ArielTeachBackInteraction.objects.filter(pk=interaction_id, teaching_session_id=session_id).first()
    if not interaction:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if request.data.get("required_artefact_type"):
        interaction.required_artefact_type = request.data.get("required_artefact_type", "")
    if interaction.await_artefact():
        interaction.save()
    serializer = ArielTeachBackInteractionSerializer(interaction)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def skip_teach_back_interaction(request, session_id, interaction_id):
    """Skip a teach-back interaction."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    interaction = ArielTeachBackInteraction.objects.filter(pk=interaction_id, teaching_session_id=session_id).first()
    if not interaction:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    interaction = SkipArielTeachBackInteractionService.execute(interaction=interaction, learner_id=request.user.id)
    serializer = ArielTeachBackInteractionSerializer(interaction)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_teach_back_interaction(request, session_id, interaction_id):
    """Cancel a teach-back interaction."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    interaction = ArielTeachBackInteraction.objects.filter(pk=interaction_id, teaching_session_id=session_id).first()
    if not interaction:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    interaction = CancelArielTeachBackInteractionService.execute(interaction=interaction, learner_id=request.user.id)
    serializer = ArielTeachBackInteractionSerializer(interaction)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def teach_back_from_artefact(request, session_id):
    """Teach Ariel from an explicitly approved Study Lab artefact reference."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    workspace_id = request.data.get("workspace_id")
    artefact_id = request.data.get("artefact_id")
    learner_explanation = request.data.get("learner_explanation", "")
    if not workspace_id or not artefact_id or not learner_explanation:
        return Response({"detail": "workspace_id, artefact_id, and learner_explanation are required."}, status=status.HTTP_400_BAD_REQUEST)

    interaction, turn, knowledge, decision, artefact = TeachArielFromArtefactService.execute(
        identity=session.identity,
        teaching_session=session,
        learner_id=request.user.id,
        workspace_id=workspace_id,
        artefact_id=artefact_id,
        learner_explanation=learner_explanation,
        concept_reference=request.data.get("concept_reference", ""),
        source_memory_unit_id=request.data.get("source_memory_unit_id"),
        create_memory=bool(request.data.get("create_memory", False)),
    )
    payload = ArielTeachBackInteractionSerializer(interaction).data
    payload["learner_response_turn_id"] = str(turn.id)
    payload["artefact_id"] = str(artefact.id)
    payload["artefact_type"] = artefact.artefact_type
    payload["strategy"] = decision["strategy"]
    payload["prompt_text"] = decision["prompt_text"]
    payload["transformation_type"] = decision["transformation_type"]
    if knowledge is not None:
        payload["knowledge_unit_id"] = str(knowledge.id)
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_teach_back_misunderstanding(request, session_id, interaction_id):
    """Return a learner-safe misunderstanding summary for a teach-back interaction."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    interaction = ArielTeachBackInteraction.objects.filter(pk=interaction_id, teaching_session_id=session_id).first()
    if not interaction or interaction.source_memory_unit_id is None:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return Response(ResolveArielMisunderstandingService.execute(source_memory_unit=interaction.source_memory_unit))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def correct_teach_back_misunderstanding(request, session_id, interaction_id):
    """Create a correction turn for a misunderstood Ariel memory."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    interaction = ArielTeachBackInteraction.objects.filter(pk=interaction_id, teaching_session_id=session_id).first()
    if not interaction or interaction.source_memory_unit_id is None:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    interaction, turn, knowledge, misunderstanding = CorrectArielMisunderstandingService.execute(
        identity=session.identity,
        teaching_session=session,
        learner_id=request.user.id,
        source_memory_unit_id=interaction.source_memory_unit_id,
        correction_text=request.data["correction_text"],
        concept_reference=request.data.get("concept_reference", ""),
        create_memory=bool(request.data.get("create_memory", True)),
        interaction=interaction,
    )
    payload = ArielTeachBackInteractionSerializer(interaction).data
    payload["learner_response_turn_id"] = str(turn.id)
    payload["misunderstanding_status"] = misunderstanding["status"]
    payload["misunderstanding_summary"] = misunderstanding["summary"]
    if knowledge is not None:
        payload["knowledge_unit_id"] = str(knowledge.id)
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def request_delayed_reteach(request, session_id, interaction_id):
    """Request a delayed reteaching interaction for the source memory of an existing interaction."""
    session = ArielTeachingSession.objects.filter(pk=session_id).first()
    if not session:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    interaction = ArielTeachBackInteraction.objects.filter(pk=interaction_id, teaching_session_id=session_id).first()
    if not interaction or interaction.source_memory_unit_id is None:
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    if not ArielAuthorizationService.is_learner_owner(request.user.id, session.identity_id):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    reteach_interaction, eligibility = CreateDelayedReteachingInteractionService.execute(
        identity=session.identity,
        teaching_session=session,
        learner_id=request.user.id,
        source_memory_unit_id=interaction.source_memory_unit_id,
        interaction=interaction,
    )
    payload = ArielTeachBackInteractionSerializer(reteach_interaction).data
    payload["eligibility_status"] = eligibility["status"]
    payload["eligibility_reason"] = eligibility["reason_code"]
    return Response(payload, status=status.HTTP_201_CREATED)
