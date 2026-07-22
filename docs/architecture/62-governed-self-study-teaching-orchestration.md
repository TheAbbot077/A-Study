# PI-6F.8 Governed Self-Study Teaching Orchestration

PI-6F.8 starts governed self-study teaching from a current PI-6F.7 preparation. It creates session-local teaching nodes, builds bounded context snapshots, generates citation-grounded learner-facing turns, records learner turns as interaction evidence, and delegates any evidence evaluation to downstream services.

It does not award mastery, alter curriculum authority, recalculate coverage, remap evidence, browse for resources, or create assessments.

## Authority Inputs

A teaching session may start only from:

- an active self-study intent;
- an active PI-6F.6 bridge plan;
- a ready PI-6F.7 preparation manifest;
- verified teaching retrieval publication;
- matching graph, bridge-plan, coverage, preparation, and retrieval fingerprints;
- tenant and learner authorization.

Authority validation is implemented in application services, not views or tasks.

## Session Lifecycle

`SelfStudyTeachingSession` tracks the learner journey:

- `PENDING`
- `ACTIVE`
- `PAUSED`
- `AWAITING_LEARNER`
- `AWAITING_EVIDENCE`
- `NODE_COMPLETE`
- `BLOCKED`
- `STALE`
- `INVALIDATED`
- `COMPLETED`
- `CANCELLED`

`TeachingSessionNode` is an immutable session-local projection of a bridge-plan node. It keeps the bridge node, graph node, teaching pack, plan ordinal, topological layer, bridge disposition, permitted roles, and context fingerprint.

Transitions are explicit and version checked. Revisit requests are recorded without rewriting official plan order.

## Teaching Turns

`TeachingTurn` is immutable. Corrections or retries create new turns.

Supported actions include:

- `INTRODUCE`
- `EXPLAIN`
- `ILLUSTRATE`
- `ASK`
- `PRACTICE`
- `CHECK_UNDERSTANDING`
- `PROVIDE_FEEDBACK`
- `REFLECT`
- `RECAP`
- `PAUSE`
- `REQUEST_REVIEW`
- `REQUEST_EVALUATION`

Generated turns use deterministic governed text for now. The model boundary records provider/model/prompt-policy versions and validates that generated material remains inside the prepared context. This preserves the future provider seam without granting a model authority over graph, plan, mastery, retrieval, privacy, or safety.

## Context and Retrieval

`TeachingContextSnapshot` freezes:

- current session and node;
- graph and bridge-plan fingerprints;
- preparation and retrieval fingerprints;
- permitted teaching roles;
- bounded prior-turn references;
- current learner input;
- safety, disclosure, model, and prompt-policy versions;
- retrieval filters and assignment identities.

Retrieval is constrained to the PI-6F.7 teaching retrieval manifest and excludes `CONFLICT_WARNING` resources from ordinary explanation. Each source-grounded turn writes `TeachingTurnCitation` records with teaching-pack resource, evidence unit, resource, extraction provenance, mapping class, teaching role, retrieval identity, citation snapshot, and citation fingerprint.

## Evidence and Mastery Boundary

Learner turns are recorded as interaction evidence inside the teaching session. PI-6F.8 can request evidence evaluation, but it does not write `MasteryDecision`, `MasteryProfile`, grades, credits, or credentials.

`NODE_COMPLETE` and `COMPLETED` are session states only. A finding explicitly records `TEACHING_COMPLETION_NOT_MASTERY` when a node is completed.

## Safety and Privacy

Learner text, retrieved text, and generated text are treated as untrusted. Prompt-injection patterns block normal generation and record a stable finding. Context snapshots exclude raw diagnostic answers and hidden model prompts.

## APIs

The self-study API exposes:

- `GET/POST /api/self-study/teaching-sessions/`
- `GET /api/self-study/teaching-sessions/{session_id}/`
- `GET /api/self-study/teaching-sessions/{session_id}/current-node/`
- `GET /api/self-study/teaching-sessions/{session_id}/nodes/`
- `GET /api/self-study/teaching-sessions/{session_id}/turns/`
- `GET /api/self-study/teaching-sessions/{session_id}/citations/`
- `GET /api/self-study/teaching-sessions/{session_id}/findings/`
- `GET /api/self-study/teaching-sessions/{session_id}/context/`
- `GET /api/self-study/teaching-sessions/{session_id}/transitions/`
- `POST /api/self-study/teaching-sessions/{session_id}/start/`
- `POST /api/self-study/teaching-sessions/{session_id}/next-turn/`
- `POST /api/self-study/teaching-sessions/{session_id}/learner-turn/`
- `POST /api/self-study/teaching-sessions/{session_id}/pause/`
- `POST /api/self-study/teaching-sessions/{session_id}/resume/`
- `POST /api/self-study/teaching-sessions/{session_id}/revisit/`
- `POST /api/self-study/teaching-sessions/{session_id}/request-evaluation/`
- `POST /api/self-study/teaching-sessions/{session_id}/complete-node/`
- `POST /api/self-study/teaching-sessions/{session_id}/advance/`
- `POST /api/self-study/teaching-sessions/{session_id}/invalidate/`
- `GET /api/self-study/teaching-sessions/{session_id}/handoff/`

History routes are paginated. Mutating routes use expected versions and learner ownership or governance authority.

## Workers and Events

Identifier-only tasks:

- `self_study.prepare_teaching_turn`
- `self_study.generate_teaching_turn`
- `self_study.record_teaching_evidence`
- `self_study.advance_teaching_session`

Events:

- `self_study.teaching_session.created`
- `self_study.teaching_session.started`
- `self_study.teaching_turn.requested`
- `self_study.teaching_turn.generated`
- `self_study.teaching_turn.recorded`
- `self_study.teaching_turn.failed`
- `self_study.teaching_evidence.requested`
- `self_study.teaching_session.paused`
- `self_study.teaching_session.resumed`
- `self_study.teaching_session.node_completed`
- `self_study.teaching_session.advanced`
- `self_study.teaching_session.blocked`
- `self_study.teaching_session.stale`
- `self_study.teaching_session.invalidated`
- `self_study.teaching_session.completed`

Events contain identifiers and bounded summaries only.

## Manual Validation

Run Docker validation after review. This implementation was not validated during creation.
