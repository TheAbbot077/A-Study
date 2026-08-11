"""
Ariel regression tests including negative tests for constitutional enforcement.

Verifies:
- Identity ownership
- Constitution enforcement
- Learner-only provenance
- Rejection of retrieval/curriculum/Abbot/answer-key injection
- Reinforcement, forgetting, corrections, contradictions, reset
- Privacy and institutional isolation
- Capabilities
- Events
- APIs
- Deterministic behavior
"""

import pytest
from django.core.exceptions import ValidationError

from apps.ariel.application.services import (
    ArielAuthorizationService,
    ArielIdentityService,
    ArielTeachingService,
    ConstitutionEnforcementService,
)
from apps.ariel.domain.models import (
    ArielCapability,
    ArielConstitution,
    ArielIdentity,
    ArielIdentityStatus,
    ArielKnowledgeUnit,
    ArielMemoryRecord,
    ArielRelationship,
    ArielTeachingSession,
    ArielTeachingTurn,
    TeachingTurnDisposition,
    ArielUserCapability,
    ConsentState,
    ConstitutionRule,
    InstitutionalVisibility,
    KnowledgeProvenance,
    MemoryState,
    TeachingTurnActor,
)
from apps.users.domain.models import Institution, User


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def constitution(db):
    return ArielConstitution.objects.create(
        version="1.0",
        rules=[
            {"code": ConstitutionRule.ARIEL_LEARNS_ONLY_FROM_LEARNER},
            {"code": ConstitutionRule.ARIEL_DOES_NOT_TEACH},
            {"code": ConstitutionRule.ARIEL_DOES_NOT_GRADE},
            {"code": ConstitutionRule.ARIEL_DOES_NOT_CONFIRM_MASTERY},
            {"code": ConstitutionRule.ARIEL_DOES_NOT_ACCESS_RETRIEVAL},
            {"code": ConstitutionRule.ARIEL_DOES_NOT_ACCESS_CURRICULUM},
            {"code": ConstitutionRule.ARIEL_DOES_NOT_ACCESS_ANSWER_KEYS},
            {"code": ConstitutionRule.ARIEL_MAY_BE_UNCERTAIN},
            {"code": ConstitutionRule.ARIEL_MAY_FORGET},
            {"code": ConstitutionRule.ARIEL_MAY_RETAIN_MISCONCEPTIONS},
            {"code": ConstitutionRule.ARIEL_MEMORY_REQUIRES_PROVENANCE},
        ],
        description="Initial Ariel Constitution",
        is_active=True,
    )


@pytest.fixture
def learner(db):
    return User.objects.create_user(email="learner@test.com", password="testpass123")


@pytest.fixture
def other_learner(db):
    return User.objects.create_user(email="other@test.com", password="testpass123")


@pytest.fixture
def institution(db):
    return Institution.objects.create(
        name="Test University",
        slug="test-university",
        institution_type="university",
    )


@pytest.fixture
def ariel_identity(db, constitution, learner):
    identity = ArielIdentityService.create_identity(
        learner_id=learner.id,
        constitution=constitution,
    )
    ArielIdentityService.activate_identity(identity)
    identity.refresh_from_db()
    return identity


@pytest.fixture
def teaching_session(db, ariel_identity, learner):
    return ArielTeachingService.start_teaching_session(
        identity=ariel_identity,
        learner_id=learner.id,
    )


@pytest.fixture
def teaching_turn(db, teaching_session):
    return ArielTeachingService.add_teaching_turn(
        session=teaching_session,
        actor=TeachingTurnActor.LEARNER,
        content="Photosynthesis is how plants make food from sunlight.",
        disposition=TeachingTurnDisposition.TEACHING,
    )


# ============================================================================
# Identity Tests
# ============================================================================

@pytest.mark.django_db
def test_create_ariel_identity(db, constitution, learner):
    """Test creating an Ariel identity."""
    identity = ArielIdentityService.create_identity(
        learner_id=learner.id,
        constitution=constitution,
    )
    assert identity.status == ArielIdentityStatus.DRAFT
    assert identity.learner_id == learner.id
    assert identity.constitution_id == constitution.id


@pytest.mark.django_db
def test_one_active_ariel_per_learner(db, constitution, learner, ariel_identity):
    """Test that only one active Ariel can exist per learner."""
    with pytest.raises(ValidationError, match="already has an active Ariel"):
        ArielIdentityService.create_identity(
            learner_id=learner.id,
            constitution=constitution,
        )


@pytest.mark.django_db
def test_activate_ariel(db, ariel_identity):
    """Test activating an Ariel identity."""
    assert ariel_identity.status == ArielIdentityStatus.ACTIVE
    assert ariel_identity.activated_at is not None


@pytest.mark.django_db
def test_suspend_ariel(db, ariel_identity):
    """Test suspending an Ariel identity."""
    ArielIdentityService.suspend_identity(ariel_identity)
    ariel_identity.refresh_from_db()
    assert ariel_identity.status == ArielIdentityStatus.SUSPENDED


@pytest.mark.django_db
def test_relationship_created_with_identity(db, ariel_identity):
    """Test that a relationship is created with the identity."""
    relationship = ArielRelationship.objects.get(identity=ariel_identity)
    assert relationship.consent_state == ConsentState.PENDING
    assert relationship.institutional_visibility == InstitutionalVisibility.PRIVATE


@pytest.mark.django_db
def test_learner_capabilities_granted(db, ariel_identity, learner):
    """Test that learner capabilities are granted on identity creation."""
    caps = ArielAuthorizationService.get_user_capabilities(learner.id, ariel_identity.id)
    assert ArielCapability.ARIEL_USE in caps
    assert ArielCapability.ARIEL_VIEW_MEMORY in caps
    assert ArielCapability.ARIEL_CORRECT_MEMORY in caps
    assert ArielCapability.ARIEL_FORGET_MEMORY in caps
    assert ArielCapability.ARIEL_RESET in caps
    assert ArielCapability.ARIEL_EXPORT in caps
    assert ArielCapability.ARIEL_SUSPEND in caps


# ============================================================================
# Constitution Enforcement Tests
# ============================================================================

@pytest.mark.django_db
def test_constitution_learner_only_teaching(db, constitution):
    """Test that constitution enforces learner-only teaching."""
    ConstitutionEnforcementService.validate_learner_teaching(constitution)


@pytest.mark.django_db
def test_constitution_no_retrieval_access(db, constitution):
    """Test that constitution blocks retrieval access."""
    ConstitutionEnforcementService.validate_no_retrieval_access(constitution)


@pytest.mark.django_db
def test_constitution_no_curriculum_access(db, constitution):
    """Test that constitution blocks curriculum access."""
    ConstitutionEnforcementService.validate_no_curriculum_access(constitution)


@pytest.mark.django_db
def test_constitution_no_answer_key_access(db, constitution):
    """Test that constitution blocks answer key access."""
    ConstitutionEnforcementService.validate_no_answer_key_access(constitution)


# ============================================================================
# Negative Tests - Injection Rejection
# ============================================================================

@pytest.mark.django_db
def test_reject_curriculum_injection(db):
    """Test that curriculum cannot directly create Ariel memory."""
    with pytest.raises(ValidationError, match="cannot originate from curriculum"):
        ConstitutionEnforcementService.reject_curriculum_injection()


@pytest.mark.django_db
def test_reject_retrieval_injection(db):
    """Test that retrieval cannot directly create Ariel memory."""
    with pytest.raises(ValidationError, match="cannot originate from retrieval"):
        ConstitutionEnforcementService.reject_retrieval_injection()


@pytest.mark.django_db
def test_reject_abbot_injection(db):
    """Test that Abbot cannot directly create Ariel memory."""
    with pytest.raises(ValidationError, match="cannot originate from Abbot"):
        ConstitutionEnforcementService.reject_abbot_injection()


@pytest.mark.django_db
def test_reject_answer_key_injection(db):
    """Test that answer keys cannot directly create Ariel memory."""
    with pytest.raises(ValidationError, match="cannot originate from answer keys"):
        ConstitutionEnforcementService.reject_answer_key_injection()


@pytest.mark.django_db
def test_knowledge_only_from_teaching_turns(db, teaching_session):
    """Test that knowledge can only be created from teaching turns, not conversation."""
    conversation_turn = ArielTeachingService.add_teaching_turn(
        session=teaching_session,
        actor=TeachingTurnActor.LEARNER,
        content="Hello Ariel!",
        disposition=TeachingTurnDisposition.CONVERSATION,
    )
    with pytest.raises(ValidationError, match="only be created from teaching turns"):
        ArielTeachingService.create_knowledge_from_teaching(
            session=teaching_session,
            teaching_turn=conversation_turn,
            normalized_statement="Hello",
        )


# ============================================================================
# Teaching & Knowledge Tests
# ============================================================================

@pytest.mark.django_db
def test_create_knowledge_from_teaching(db, teaching_session, teaching_turn):
    """Test creating knowledge from a teaching turn."""
    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Photosynthesis converts sunlight to energy",
        confidence=0.7,
    )
    assert knowledge.memory_state == MemoryState.NEW
    assert knowledge.provenance == KnowledgeProvenance.LEARNER_TEACHING
    assert float(knowledge.confidence) == 0.7


@pytest.mark.django_db
def test_knowledge_provenance_is_learner(db, teaching_session, teaching_turn):
    """Test that knowledge provenance is always learner-originated."""
    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Test statement",
    )
    assert knowledge.provenance in KnowledgeProvenance.values
    assert knowledge.provenance != "curriculum"
    assert knowledge.provenance != "retrieval"
    assert knowledge.provenance != "abbot"


@pytest.mark.django_db
def test_reinforce_knowledge(db, teaching_session, teaching_turn):
    """Test reinforcing knowledge."""
    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Test statement",
    )
    assert knowledge.memory_state == MemoryState.NEW

    # Add a reinforcement turn
    reinforce_turn = ArielTeachingService.add_teaching_turn(
        session=teaching_session,
        actor=TeachingTurnActor.LEARNER,
        content="Let me teach you again: photosynthesis is important.",
        disposition=TeachingTurnDisposition.REINFORCEMENT,
    )

    knowledge = ArielTeachingService.reinforce_knowledge(
        knowledge=knowledge,
        teaching_turn=reinforce_turn,
        new_confidence=0.8,
    )
    assert knowledge.memory_state == MemoryState.FRAGILE
    assert float(knowledge.confidence) == 0.8


@pytest.mark.django_db
def test_correct_knowledge_preserves_history(db, teaching_session, teaching_turn):
    """Test that corrections preserve history."""
    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Plants eat sunlight",
    )

    correction_turn = ArielTeachingService.add_teaching_turn(
        session=teaching_session,
        actor=TeachingTurnActor.LEARNER,
        content="Actually, plants don't eat sunlight, they convert it.",
        disposition=TeachingTurnDisposition.CORRECTION,
    )

    new_knowledge = ArielTeachingService.correct_knowledge(
        old_knowledge=knowledge,
        teaching_turn=correction_turn,
        new_normalized_statement="Plants convert sunlight to energy",
        correction_reason="Clarification",
    )

    knowledge.refresh_from_db()
    assert knowledge.memory_state == MemoryState.SUPERSEDED
    assert knowledge.superseded_by_id == new_knowledge.id
    assert new_knowledge.provenance == KnowledgeProvenance.LEARNER_CORRECTION


@pytest.mark.django_db
def test_forget_knowledge(db, teaching_session, teaching_turn):
    """Test forgetting knowledge."""
    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Test statement",
    )
    knowledge = ArielTeachingService.forget_knowledge(knowledge)
    assert knowledge.memory_state == MemoryState.FORGOTTEN
    assert knowledge.forgotten_at is not None


@pytest.mark.django_db
def test_forgetting_preserves_provenance(db, teaching_session, teaching_turn):
    """Test that forgetting preserves provenance."""
    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Test statement",
    )
    original_provenance = knowledge.provenance
    knowledge = ArielTeachingService.forget_knowledge(knowledge)
    assert knowledge.provenance == original_provenance


@pytest.mark.django_db
def test_mark_contradiction_preserves_both(db, teaching_session, teaching_turn):
    """Test that contradictions preserve both memories."""
    knowledge1 = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="The sky is blue",
    )

    turn2 = ArielTeachingService.add_teaching_turn(
        session=teaching_session,
        actor=TeachingTurnActor.LEARNER,
        content="Actually, the sky is green",
        disposition=TeachingTurnDisposition.TEACHING,
    )
    knowledge2 = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=turn2,
        normalized_statement="The sky is green",
    )

    ArielTeachingService.mark_contradiction(knowledge1, knowledge2)

    knowledge1.refresh_from_db()
    knowledge2.refresh_from_db()
    assert knowledge1.memory_state == MemoryState.CONFLICTED
    assert knowledge2.memory_state == MemoryState.CONFLICTED


@pytest.mark.django_db
def test_reset_preserves_audit_history(db, teaching_session, teaching_turn):
    """Test that reset preserves audit history."""
    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Test statement",
    )

    # Record exists before reset
    assert ArielMemoryRecord.objects.filter(knowledge_unit=knowledge).count() > 0

    ArielIdentityService.reset_identity(teaching_session.identity)

    # Memory records still exist after reset
    assert ArielMemoryRecord.objects.filter(knowledge_unit=knowledge).count() > 0
    knowledge.refresh_from_db()
    assert knowledge.memory_state == MemoryState.FORGOTTEN


# ============================================================================
# Privacy & Authorization Tests
# ============================================================================

@pytest.mark.django_db
def test_only_owner_can_teach(db, ariel_identity, other_learner):
    """Test that only the owning learner can teach Ariel."""
    with pytest.raises(ValidationError, match="Only the owning learner"):
        ArielTeachingService.start_teaching_session(
            identity=ariel_identity,
            learner_id=other_learner.id,
        )


@pytest.mark.django_db
def test_institution_cannot_access_transcripts(db):
    """Test that institutions cannot access Ariel transcripts by default."""
    assert ArielAuthorizationService.can_institution_access_transcripts("user-id", "identity-id") is False


@pytest.mark.django_db
def test_admin_cannot_browse_transcripts(db):
    """Test that administrators cannot browse Ariel transcripts."""
    assert ArielAuthorizationService.can_admin_browse_transcripts("user-id", "identity-id") is False


@pytest.mark.django_db
def test_non_owner_cannot_view_memory(db, ariel_identity, other_learner):
    """Test that non-owners cannot view memory."""
    assert not ArielAuthorizationService.is_learner_owner(other_learner.id, ariel_identity.id)


@pytest.mark.django_db
def test_owner_can_view_memory(db, ariel_identity, learner):
    """Test that the owner can view memory."""
    assert ArielAuthorizationService.is_learner_owner(learner.id, ariel_identity.id)


# ============================================================================
# Memory Record Tests
# ============================================================================

@pytest.mark.django_db
def test_memory_record_created_on_knowledge_creation(db, teaching_session, teaching_turn):
    """Test that a memory record is created when knowledge is created."""
    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Test statement",
    )
    records = ArielMemoryRecord.objects.filter(knowledge_unit=knowledge)
    assert records.count() == 1
    assert records.first().transition_reason == "KNOWLEDGE_CREATED"


@pytest.mark.django_db
def test_memory_record_created_on_forgetting(db, teaching_session, teaching_turn):
    """Test that a memory record is created when knowledge is forgotten."""
    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Test statement",
    )
    ArielTeachingService.forget_knowledge(knowledge)
    records = ArielMemoryRecord.objects.filter(
        knowledge_unit=knowledge,
        new_state=MemoryState.FORGOTTEN,
    )
    assert records.count() == 1


# ============================================================================
# Event Tests
# ============================================================================

@pytest.mark.django_db
def test_ariel_identity_created_event(db, constitution, learner):
    """Test that identity creation produces correct event payload."""
    from apps.ariel.domain.events import ArielIdentityCreated

    identity = ArielIdentityService.create_identity(
        learner_id=learner.id,
        constitution=constitution,
    )
    event = ArielIdentityCreated(
        identity_id=identity.id,
        learner_id=learner.id,
        constitution_version=constitution.version,
    )
    payload = event.payload()
    assert payload["identity_id"] == str(identity.id)
    assert payload["learner_id"] == str(learner.id)
    assert payload["constitution_version"] == "1.0"
    assert event.event_type == "ariel.identity.created"


@pytest.mark.django_db
def test_knowledge_created_event(db, teaching_session, teaching_turn):
    """Test that knowledge creation produces correct event payload."""
    from apps.ariel.domain.events import KnowledgeCreated

    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Test statement",
    )
    event = KnowledgeCreated(
        knowledge_id=knowledge.id,
        identity_id=teaching_session.identity_id,
        learner_id=teaching_session.learner_id,
        session_id=teaching_session.id,
        turn_id=teaching_turn.id,
    )
    payload = event.payload()
    assert payload["knowledge_id"] == str(knowledge.id)
    assert "normalized_statement" not in payload  # Identifier-only


# ============================================================================
# Deterministic Behavior Tests
# ============================================================================

@pytest.mark.django_db
def test_deterministic_memory_states(db):
    """Test that memory states are deterministic and well-defined."""
    states = MemoryState.values
    assert "new" in states
    assert "fragile" in states
    assert "reinforced" in states
    assert "stable" in states
    assert "conflicted" in states
    assert "misconceived" in states
    assert "forgotten" in states
    assert "superseded" in states
    assert "retracted" in states


@pytest.mark.django_db
def test_confidence_bounds(db, teaching_session, teaching_turn):
    """Test that confidence is bounded between 0 and 1."""
    knowledge = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Test",
        confidence=0.0,
    )
    assert float(knowledge.confidence) == 0.0

    knowledge2 = ArielTeachingService.create_knowledge_from_teaching(
        session=teaching_session,
        teaching_turn=teaching_turn,
        normalized_statement="Test 2",
        confidence=1.0,
    )
    assert float(knowledge2.confidence) == 1.0