# PI-8C.2 — Ariel Constitution & Learner-Taught Memory Platform

## Strategic Objective

Introduce Ariel as a governed learner companion whose knowledge, uncertainty, misconceptions, memory, and growth originate exclusively from explicit learner teaching.

Ariel is not another tutor. Ariel is not another retrieval engine. Ariel is not another assessment engine. Ariel is not another Abbot. She is a learner.

## Product Constitution

The implementation makes the following promise technically enforceable:

**Ariel knows only what her learner has explicitly taught her.**

She may remember. She may forget. She may misunderstand. She may improve. She may ask questions. She may become uncertain. She must never silently inherit academic knowledge from the platform.

## Constitutional Boundary

Ariel must never receive academic knowledge directly from:
- Curriculum graphs
- Retrieval indexes
- Teaching retrieval assemblies
- Abbot instructional responses
- Assessment answer keys
- Mastery projections
- Competency graphs
- Institutional analytics
- Uploaded resources
- Hidden prompts containing academic answers

The only source of Ariel academic knowledge is governed learner teaching.

## Bounded Context

```
apps/ariel/
├── __init__.py
├── apps.py
├── admin.py
├── tasks.py
├── api/
│   ├── __init__.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── application/
│   ├── __init__.py
│   └── services.py
├── domain/
│   ├── __init__.py
│   ├── models.py
│   └── events.py
├── infrastructure/
│   └── __init__.py
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
└── tests/
    ├── __init__.py
    └── test_ariel_constitution.py
```

## Core Aggregates

### ArielIdentity
The governed learner companion. One active Ariel per learner.
- Learner ownership
- Institution reference (optional)
- Lifecycle: draft → active → suspended → archived
- Constitution version reference

### ArielRelationship
Explicit learner-Ariel relationship with privacy and consent.
- Consent state: pending → granted → withdrawn
- Institutional visibility: private, metadata_only, aggregate
- Privacy and retention policies

### ArielConstitution
Versioned constitution governing all Ariel sessions.
- Rules enforced through application services
- Versioned for traceability

### ArielTeachingSession
Durable learner teaching session.
- References identity, learner, constitution
- Optional learning journey, subject, concept references
- Lifecycle: active → completed/abandoned

### ArielTeachingTurn
Learner-visible conversation turn. Never stores hidden reasoning.
- Actor: learner or Ariel
- Disposition: conversation, teaching, correction, reinforcement, forgetting, inspection, question
- Provenance tracking
- Resulting memory effect

### ArielKnowledgeUnit
Every knowledge item originates from explicit learner teaching.
- Normalized statement
- Confidence (Ariel's confidence, not objective correctness)
- Memory state
- Provenance (always learner-originated)
- Supersession tracking
- Forgetting metadata

### ArielMemoryRecord
Memory state transition history.
- Previous and new states
- Transition reason
- Provenance

### ArielMisconception
Preserves incorrect learner teaching as educational history.
- Original explanation
- Resulting belief
- Contradiction and correction history

### ArielCorrectionRecord
Durable correction record preserving provenance and history.
- Superseded knowledge
- Replacement knowledge
- Teaching turn reference

### ArielReinforcementRecord
Tracks reinforcement history independent from learner evidence.
- Previous and updated confidence
- State transitions

## Constitution Rules

- ARIEL_LEARNS_ONLY_FROM_LEARNER
- ARIEL_DOES_NOT_TEACH
- ARIEL_DOES_NOT_GRADE
- ARIEL_DOES_NOT_CONFIRM_MASTERY
- ARIEL_DOES_NOT_ACCESS_RETRIEVAL
- ARIEL_DOES_NOT_ACCESS_CURRICULUM
- ARIEL_DOES_NOT_ACCESS_ANSWER_KEYS
- ARIEL_MAY_BE_UNCERTAIN
- ARIEL_MAY_FORGET
- ARIEL_MAY_RETAIN_MISCONCEPTIONS
- ARIEL_MEMORY_REQUIRES_PROVENANCE

## Memory States

- NEW → FRAGILE → REINFORCED → STABLE
- CONFLICTED (contradictions preserved)
- MISCONCEIVED (incorrect teaching preserved)
- FORGOTTEN (deterministic forgetting)
- SUPERSEDED (corrections)
- RETRACTED (learner retraction)

## Explicit Teaching Contract

Ordinary conversation does not update Ariel memory. Memory updates occur only during governed learner teaching:
- Teach Ariel
- Correct Ariel
- Explain to Ariel
- Review with Ariel
- Show Ariel

## Privacy Model

Ariel memory belongs to the learner. Institutional users cannot access:
- Teaching transcripts
- Misconceptions
- Private explanations
- Correction history
- Reflective content

Institutions may configure availability, retention, and consent requirements but do not own Ariel memory.

## Capability Model

- ARIEL_USE
- ARIEL_VIEW_MEMORY
- ARIEL_CORRECT_MEMORY
- ARIEL_FORGET_MEMORY
- ARIEL_RESET
- ARIEL_EXPORT
- ARIEL_SUSPEND
- ARIEL_ADMIN_STATUS
- ARIEL_ADMIN_SUSPEND
- ARIEL_ADMIN_RESTORE
- ARIEL_ADMIN_VIEW_AUDIT

Administrative capabilities never imply transcript access.

## Events

Identifier-only payloads, idempotent:
- ArielIdentityCreated
- ArielActivated
- TeachingSessionStarted
- LearnerTaughtAriel
- KnowledgeCreated
- MemoryReinforced
- MemoryCorrected
- MemoryForgotten
- MemoryConflicted
- MemoryRetracted
- ArielReset

## APIs

Backend APIs for:
- Identity lifecycle (create, get, activate, suspend, reset)
- Teaching sessions (start, list)
- Teaching turns (add, list)
- Knowledge (create, list, reinforce, correct, forget, retract)
- Memory records (list, export)

## Compatibility

This increment does not alter:
- Educational Organization authority
- Learning Identity
- Learning Journeys
- Self Study
- Evidence
- Mastery
- Retrieval
- Curriculum Governance
- Notifications
- Audit

No existing capability interprets Ariel activity as proof of learning.

## Non-Goals

- Frontend experience
- Avatars, animation, voice, emotional simulation
- Assessment, grading, evidence generation
- Mastery updates
- Curriculum validation
- Retrieval grounding
- Institutional dashboards
- Study Lab
- Lesson studies

## Validation

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend pytest apps/ariel
docker compose exec backend pytest apps/learning_identity
docker compose exec backend pytest apps/learning_journeys
docker compose exec backend pytest
```

## Success Criteria

- [x] Ariel exists as a learner-owned governed identity
- [x] Ariel's constitution is explicit and versioned
- [x] Ariel learns only through explicit learner teaching
- [x] Every memory has verifiable provenance
- [x] Ariel can reinforce, forget, misunderstand, and be corrected
- [x] Contradictions preserve history instead of overwriting it
- [x] Learners fully control Ariel's memory lifecycle
- [x] Institutions cannot access Ariel's private memory by default
- [x] Ariel activity never alters mastery or evidence
- [x] Events, APIs, audit, documentation, admin, and regression tests are complete
- [x] The platform is prepared for PI-8C.3