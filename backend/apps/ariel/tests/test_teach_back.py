"""
PI-8C.7 teach-back regression tests.

These tests cover deterministic strategy resolution, lifecycle transitions,
and identifier-only events without introducing any assessment semantics.
"""

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.ariel.application.services import (
    ArielIdentityService,
    ArielTeachBackTemplateRegistry,
    ArielTeachingService,
    CancelArielTeachBackInteractionService,
    RecordTeachBackResponseService,
    ResolveArielTeachBackStrategyService,
    ResolveArielMisunderstandingService,
    ResolveDelayedReteachingService,
    SkipArielTeachBackInteractionService,
    StartArielTeachBackInteractionService,
    TeachArielFromArtefactService,
    CreateDelayedReteachingInteractionService,
    CorrectArielMisunderstandingService,
)
from apps.ariel.domain.events import (
    ArielDelayedReteachingRequested,
    ArielMisunderstandingCorrected,
    ArielMisunderstandingPresented,
    ArielTeachBackPresented,
    ArielTeachBackResponded,
    ArielTeachBackStarted,
    ArielTeachingTransformationCompleted,
    ArielTeachingTransformationRequested,
)
from apps.ariel.domain.models import (
    ArielConstitution,
    ArielIdentity,
    ArielKnowledgeUnit,
    ArielTeachBackInteraction,
    ArielIdentityStatus,
    MemoryState,
    TeachingInputProvenance,
    TeachBackInteractionStatus,
    TeachBackInteractionType,
    TeachingTurnActor,
    TeachingTurnDisposition,
)
from apps.users.domain.models import User
from apps.study_lab.application.interoperability_services import CreateStudyArtefactService
from apps.study_lab.application.services import CreateStudyWorkspaceService
from apps.study_lab.domain.enums import StudyArtefactOrigin, StudyArtefactType, WorkspaceType


@pytest.fixture
def constitution(db):
    return ArielConstitution.objects.create(
        version="1.0",
        rules=[
            {"code": "ARIEL_LEARNS_ONLY_FROM_LEARNER"},
            {"code": "ARIEL_DOES_NOT_TEACH"},
            {"code": "ARIEL_DOES_NOT_GRADE"},
            {"code": "ARIEL_DOES_NOT_CONFIRM_MASTERY"},
            {"code": "ARIEL_DOES_NOT_ACCESS_RETRIEVAL"},
            {"code": "ARIEL_DOES_NOT_ACCESS_CURRICULUM"},
            {"code": "ARIEL_DOES_NOT_ACCESS_ANSWER_KEYS"},
            {"code": "ARIEL_MAY_BE_UNCERTAIN"},
            {"code": "ARIEL_MAY_FORGET"},
            {"code": "ARIEL_MAY_RETAIN_MISCONCEPTIONS"},
            {"code": "ARIEL_MEMORY_REQUIRES_PROVENANCE"},
        ],
        description="Teach-back constitution",
        is_active=True,
    )


@pytest.fixture
def learner(db):
    return User.objects.create_user(email="teach-back@test.com", password="testpass123")


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def identity(db, constitution, learner):
    identity = ArielIdentityService.create_identity(learner_id=learner.id, constitution=constitution)
    ArielIdentityService.activate_identity(identity)
    identity.refresh_from_db()
    return identity


@pytest.fixture
def teaching_session(db, identity, learner):
    return ArielTeachingService.start_teaching_session(identity=identity, learner_id=learner.id)


@pytest.fixture
def teaching_turn(db, teaching_session):
    return ArielTeachingService.add_teaching_turn(
        session=teaching_session,
        actor=TeachingTurnActor.LEARNER,
        content="Plants convert sunlight into energy.",
        disposition=TeachingTurnDisposition.TEACHING,
    )


@pytest.fixture
def source_memory(db, teaching_session, teaching_turn):
    return ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Plants convert sunlight into energy",
        confidence=0.4,
    )


@pytest.fixture
def study_workspace(db, learner):
    return CreateStudyWorkspaceService.execute(learner_id=learner.id, workspace_type=WorkspaceType.SELF_STUDY, title="Study Desk")


@pytest.fixture
def study_artefact(db, study_workspace, learner):
    return CreateStudyArtefactService.execute(
        study_workspace.id,
        learner.id,
        artefact_type=StudyArtefactType.TEXT_NOTE,
        title="Learned note",
        summary="Learner authored summary",
        creation_source=StudyArtefactOrigin.NATIVE,
        native_payload={"authorship": "LEARNER_AUTHORED", "body": "Plants convert sunlight into energy."},
    )


@pytest.mark.django_db
def test_strategy_resolver_prefers_memory_contradiction(source_memory):
    source_memory.memory_state = MemoryState.CONFLICTED
    source_memory.save()

    decision = ResolveArielTeachBackStrategyService.execute(source_memory_unit=source_memory)

    assert decision["strategy"] == TeachBackInteractionType.RESOLVE_CONTRADICTION
    assert decision["prompt_template_key"] == "TEACH_BACK_RESOLVE_CONTRADICTION_V1"
    assert decision["intensity"] == "deep"


@pytest.mark.django_db
def test_strategy_resolver_requests_transformation_for_pasted_text(source_memory):
    decision = ResolveArielTeachBackStrategyService.execute(
        source_memory_unit=source_memory,
        input_provenance=TeachingInputProvenance.PASTED_TEXT,
        concept_reference="Explain the concept in your own words",
    )

    assert decision["transformation_required"] is True
    assert decision["transformation_type"] == "restated_explanation"


@pytest.mark.django_db
def test_start_teach_back_creates_active_interaction(teaching_session, identity, learner, source_memory):
    interaction, decision = StartArielTeachBackInteractionService.execute(
        identity=identity,
        teaching_session=teaching_session,
        learner_id=learner.id,
        source_memory_unit_id=source_memory.id,
        concept_reference="How do plants convert sunlight?",
        input_provenance=TeachingInputProvenance.DIRECT_TYPED_EXPLANATION,
        auto_present=True,
    )

    interaction.refresh_from_db()
    assert interaction.status == TeachBackInteractionStatus.ACTIVE
    assert interaction.presented_at is not None
    assert interaction.prompt_template_key == decision["prompt_template_key"]


@pytest.mark.django_db
def test_response_resolves_interaction_without_assessment(teaching_session, identity, learner, source_memory):
    interaction, _ = StartArielTeachBackInteractionService.execute(
        identity=identity,
        teaching_session=teaching_session,
        learner_id=learner.id,
        source_memory_unit_id=source_memory.id,
        concept_reference="Explain the process",
        input_provenance=TeachingInputProvenance.DIRECT_TYPED_EXPLANATION,
        auto_present=True,
    )

    interaction, turn, knowledge = RecordTeachBackResponseService.execute(
        interaction=interaction,
        learner_id=learner.id,
        content="Plants use light to build sugars.",
        create_memory=False,
    )

    assert turn.content == "Plants use light to build sugars."
    assert interaction.status == TeachBackInteractionStatus.RESOLVED
    assert interaction.responded_at is not None
    assert knowledge is None


@pytest.mark.django_db
def test_skip_and_cancel_are_terminal(teaching_session, identity, learner, source_memory):
    interaction, _ = StartArielTeachBackInteractionService.execute(
        identity=identity,
        teaching_session=teaching_session,
        learner_id=learner.id,
        source_memory_unit_id=source_memory.id,
        concept_reference="Compare the ideas",
        input_provenance=TeachingInputProvenance.DIRECT_TYPED_EXPLANATION,
        auto_present=False,
    )

    interaction = SkipArielTeachBackInteractionService.execute(interaction=interaction, learner_id=learner.id)
    assert interaction.status == TeachBackInteractionStatus.SKIPPED
    with pytest.raises(ValidationError):
        CancelArielTeachBackInteractionService.execute(interaction=interaction, learner_id=learner.id)


@pytest.mark.django_db
def test_identifier_only_events(identity, teaching_session, learner):
    interaction, _ = StartArielTeachBackInteractionService.execute(
        identity=identity,
        teaching_session=teaching_session,
        learner_id=learner.id,
        concept_reference="Explain the idea",
        input_provenance=TeachingInputProvenance.DIRECT_TYPED_EXPLANATION,
        auto_present=False,
    )
    started = ArielTeachBackStarted(
        ariel_identity_id=identity.id,
        learner_id=learner.id,
        session_id=teaching_session.id,
        interaction_id=interaction.id,
        source_memory_id=None,
    )
    presented = ArielTeachBackPresented(
        ariel_identity_id=identity.id,
        learner_id=learner.id,
        session_id=teaching_session.id,
        interaction_id=interaction.id,
    )
    responded = ArielTeachBackResponded(
        ariel_identity_id=identity.id,
        learner_id=learner.id,
        session_id=teaching_session.id,
        interaction_id=interaction.id,
        learner_response_turn_id=None,
    )

    assert started.payload()["interaction_id"] == str(interaction.id)
    assert "normalized_statement" not in started.payload()
    assert presented.payload()["session_id"] == str(teaching_session.id)
    assert "learner_response_turn_id" not in responded.payload()


@pytest.mark.django_db
def test_teach_back_strategies_api(client, learner):
    client.force_authenticate(learner)
    response = client.get("/api/ariel/teach-back/strategies/")
    assert response.status_code == 200
    assert any(item["strategy"] == TeachBackInteractionType.NEW_EXAMPLE for item in response.data)


@pytest.mark.django_db
def test_teach_back_strategy_registry_is_learner_safe():
    templates = ArielTeachBackTemplateRegistry.list()
    assert any(item["strategy"] == TeachBackInteractionType.NEW_EXAMPLE for item in templates)
    assert all("answer" not in item["prompt_text"].lower() for item in templates)


@pytest.mark.django_db
def test_teach_ariel_from_artefact_creates_reference_based_turn(teaching_session, identity, learner, study_workspace, study_artefact):
    interaction, turn, knowledge, decision, artefact = TeachArielFromArtefactService.execute(
        identity=identity,
        teaching_session=teaching_session,
        learner_id=learner.id,
        workspace_id=study_workspace.id,
        artefact_id=study_artefact.id,
        learner_explanation="Plants convert sunlight into stored chemical energy.",
        concept_reference="photosynthesis",
        create_memory=False,
    )

    interaction.refresh_from_db()
    assert interaction.status == TeachBackInteractionStatus.RESOLVED
    assert turn.resulting_memory_effect["artefact_id"] == str(study_artefact.id)
    assert turn.resulting_memory_effect["authorship_classification"] == "LEARNER_AUTHORED"
    assert decision["transformation_type"] in {None, "restated_explanation", "application"}
    assert artefact.id == study_artefact.id
    assert knowledge is None


@pytest.mark.django_db
def test_misunderstanding_resolution_and_correction(teaching_session, identity, learner, source_memory):
    source_memory.memory_state = MemoryState.MISCONCEIVED
    source_memory.save()

    misunderstanding = ResolveArielMisunderstandingService.execute(source_memory_unit=source_memory)
    assert misunderstanding["status"] == "MISCONCEIVED"

    interaction, turn, knowledge, resolved = CorrectArielMisunderstandingService.execute(
        identity=identity,
        teaching_session=teaching_session,
        learner_id=learner.id,
        source_memory_unit_id=source_memory.id,
        correction_text="Plants convert sunlight into energy rather than eating it.",
        create_memory=True,
    )

    interaction.refresh_from_db()
    source_memory.refresh_from_db()
    assert interaction.status == TeachBackInteractionStatus.RESOLVED
    assert source_memory.memory_state == MemoryState.SUPERSEDED
    assert knowledge is not None
    assert resolved["status"] == "MISCONCEIVED"
    assert turn.disposition == TeachingTurnDisposition.CORRECTION


@pytest.mark.django_db
def test_delayed_reteaching_flow_uses_memory_state(teaching_session, identity, learner, source_memory):
    source_memory.memory_state = MemoryState.FRAGILE
    source_memory.save()

    eligibility = ResolveDelayedReteachingService.execute(source_memory_unit=source_memory)
    assert eligibility["status"] == "ELIGIBLE"

    interaction, eligibility2 = CreateDelayedReteachingInteractionService.execute(
        identity=identity,
        teaching_session=teaching_session,
        learner_id=learner.id,
        source_memory_unit_id=source_memory.id,
        auto_present=True,
    )

    interaction.refresh_from_db()
    assert interaction.interaction_type == TeachBackInteractionType.RETEACH_AFTER_DELAY
    assert interaction.status == TeachBackInteractionStatus.ACTIVE
    assert eligibility2["status"] == "ELIGIBLE"


@pytest.mark.django_db
def test_artefact_teach_api(client, learner, identity, teaching_session, study_workspace, study_artefact):
    client.force_authenticate(learner)
    response = client.post(
        f"/api/ariel/sessions/{teaching_session.id}/teach-back/from-artefact/",
        {
            "workspace_id": str(study_workspace.id),
            "artefact_id": str(study_artefact.id),
            "learner_explanation": "This note explains photosynthesis in my own words.",
            "concept_reference": "photosynthesis",
            "create_memory": False,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["artefact_id"] == str(study_artefact.id)
    assert response.data["learner_response_turn_id"]


@pytest.mark.django_db
def test_misunderstanding_api_and_correction_api(client, learner, identity, teaching_session, source_memory):
    client.force_authenticate(learner)
    source_memory.memory_state = MemoryState.MISCONCEIVED
    source_memory.save()
    interaction, _ = StartArielTeachBackInteractionService.execute(
        identity=identity,
        teaching_session=teaching_session,
        learner_id=learner.id,
        source_memory_unit_id=source_memory.id,
        concept_reference="correct this idea",
        input_provenance=TeachingInputProvenance.DIRECT_TYPED_EXPLANATION,
        auto_present=False,
    )

    misunderstanding = client.get(f"/api/ariel/sessions/{teaching_session.id}/teach-back/{interaction.id}/misunderstanding/")
    assert misunderstanding.status_code == 200
    assert misunderstanding.data["status"] == "MISCONCEIVED"

    correction = client.post(
        f"/api/ariel/sessions/{teaching_session.id}/teach-back/{interaction.id}/correct/",
        {"correction_text": "It is a conversion process, not eating sunlight.", "create_memory": True},
        format="json",
    )
    assert correction.status_code == 201
    assert correction.data["misunderstanding_status"] == "MISCONCEIVED"
    assert correction.data["learner_response_turn_id"]


@pytest.mark.django_db
def test_delayed_reteaching_api(client, learner, identity, teaching_session, source_memory):
    client.force_authenticate(learner)
    source_memory.memory_state = MemoryState.FRAGILE
    source_memory.save()
    interaction, _ = StartArielTeachBackInteractionService.execute(
        identity=identity,
        teaching_session=teaching_session,
        learner_id=learner.id,
        source_memory_unit_id=source_memory.id,
        concept_reference="reteach this idea",
        input_provenance=TeachingInputProvenance.DIRECT_TYPED_EXPLANATION,
        auto_present=False,
    )

    reteach = client.post(f"/api/ariel/sessions/{teaching_session.id}/teach-back/{interaction.id}/reteach/", {}, format="json")
    assert reteach.status_code == 201
    assert reteach.data["interaction_type"] == TeachBackInteractionType.RETEACH_AFTER_DELAY


@pytest.mark.django_db
def test_follow_on_events_are_identifier_only(identity, learner, teaching_session, study_artefact, source_memory):
    requested = ArielTeachingTransformationRequested(
        ariel_identity_id=identity.id,
        learner_id=learner.id,
        session_id=teaching_session.id,
        interaction_id=source_memory.id,
        artefact_id=study_artefact.id,
    )
    completed = ArielTeachingTransformationCompleted(
        ariel_identity_id=identity.id,
        learner_id=learner.id,
        session_id=teaching_session.id,
        interaction_id=source_memory.id,
        artefact_id=study_artefact.id,
    )
    delayed = ArielDelayedReteachingRequested(
        ariel_identity_id=identity.id,
        learner_id=learner.id,
        session_id=teaching_session.id,
        interaction_id=source_memory.id,
        source_memory_id=source_memory.id,
    )
    misunderstood = ArielMisunderstandingPresented(
        ariel_identity_id=identity.id,
        learner_id=learner.id,
        session_id=teaching_session.id,
        interaction_id=source_memory.id,
        source_memory_id=source_memory.id,
    )
    corrected = ArielMisunderstandingCorrected(
        ariel_identity_id=identity.id,
        learner_id=learner.id,
        session_id=teaching_session.id,
        interaction_id=source_memory.id,
        source_memory_id=source_memory.id,
    )

    assert "learner_explanation" not in requested.payload()
    assert "title" not in completed.payload()
    assert delayed.payload()["source_memory_id"] == str(source_memory.id)
    assert misunderstood.payload()["interaction_id"] == str(source_memory.id)
    assert corrected.payload()["interaction_id"] == str(source_memory.id)
