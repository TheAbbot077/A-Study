# PI-6F.1 Self-study intent, governance, and acquisition policy

## Boundary

The `self_study` bounded context records what a learner intends to achieve and
the immutable policy governing a journey. It does not resolve curricula,
diagnose placement, acquire content, process documents, or create courses.

`SelfStudyIntentActivated` is the durable integration boundary for PI-6F.2. No
PI-6F.1 service invokes a downstream worker or assumes that a consumer exists.

## Intent lifecycle

Learning mode is always explicit:

- `INSTITUTION_GOVERNED`
- `SELF_STUDY`

The lifecycle is `DRAFT`, `READY`, `ACTIVE`, `SUPERSEDED`, and `CANCELLED`.
Activation requires a meaningful goal, a workspace subject, a preferred
language, policy acknowledgement, and a valid effective-policy snapshot.
Cancelled and superseded history is retained.

Age band, accessibility context, prior qualifications, and declared
familiarity are contextual data only. They do not establish placement,
mastery, curriculum difficulty, grades, or transcript outcomes.

## Policy precedence and snapshots

Effective policy is resolved explicitly in this order:

1. Platform safety policy
2. Tenant policy
3. Learner preferences

Boolean permissions combine with logical AND, prohibitions cannot be relaxed,
numeric and monetary limits take the minimum, and allow-lists take their
intersection. A lower authority may restrict policy but cannot add permission
denied by a higher authority.

Activation resolves and validates these layers inside the activation
transaction. The resulting `EffectiveLearningPolicySnapshot` is immutable and
is linked one-to-one with the active intent. Later policy changes do not alter
historical snapshots or decisions.

The initial migration installs a reversible, fail-closed platform baseline:
allow-lists are empty, external networking is disabled, paid and
unknown-licence content are prohibited, and autonomous fallback is prohibited.
An authorised platform policy must explicitly replace that baseline before
automatic acquisition can authorize a candidate.

## Diagnostic disclosure

The backend contract always requires purpose disclosure and prevents
learner-facing serialization of:

- Raw placement scores
- Comparative ranking
- Internal model reasoning
- Chain-of-thought
- Generic internal policy state

Diagnostic placement has no formal-grade or transcript effect.

## Resource acquisition authorization

`AuthorizeResourceAcquisitionService` accepts metadata only. It does not fetch
or follow a URI, inspect a document, run extraction, or add evidence.

The deterministic result is exactly one of:

- `AUTO_APPROVED`
- `APPROVAL_REQUIRED`
- `LINK_ONLY`
- `REJECTED`

Every decision references the immutable policy snapshot, stores a canonical
fingerprint of the candidate metadata, uses stable reason codes, and supports
idempotent replay. Unknown providers, licences, MIME types, languages, costs,
sizes, and trust classifications fail closed.

External metadata cannot grant itself trusted status or alter policy. External
network access remains policy data only; PI-6F.1 does not perform downloading.

## Autonomous fallback

Autonomous curriculum fallback is denied by default. Authorization requires:

- An active `SELF_STUDY` intent
- Explicit permission in the immutable policy snapshot
- Institutional authorization for the consequential decision
- A durable curriculum-resolution failure belonging to the intent
- Stable failure reason codes

The authorization record does not generate a curriculum.

## API

Canonical routes:

- `POST /api/self-study/intents/`
- `GET|PATCH /api/self-study/intents/{intent_id}/`
- `POST /api/self-study/intents/{intent_id}/ready/`
- `POST /api/self-study/intents/{intent_id}/draft/`
- `POST /api/self-study/intents/{intent_id}/activate/`
- `POST /api/self-study/intents/{intent_id}/cancel/`
- `POST /api/self-study/intents/{intent_id}/supersede/`
- `GET /api/self-study/intents/{intent_id}/policy/`
- `PATCH /api/self-study/intents/{intent_id}/preferences/`
- `POST /api/self-study/intents/{intent_id}/authorize-resource/`
- `POST /api/self-study/intents/{intent_id}/authorize-autonomous-fallback/`

All routes require authentication. Learners see their own intents;
institutional administrators see only intents in active memberships for their
tenant. An inaccessible identifier returns the same not-found response as an
unknown identifier.

No resources-list endpoint exists because PI-6F.1 does not acquire resources.

## Events

Events contain identifiers, aggregate versions, decisions, and stable reason
codes—not goals, documents, full policy documents, or sensitive learner data.
Activation and decision events are registered with `transaction.on_commit`.

Implemented event names:

- `self_study.intent_created`
- `self_study.intent_updated`
- `self_study.intent_marked_ready`
- `self_study.intent_returned_to_draft`
- `self_study.intent_activated`
- `self_study.intent_cancelled`
- `self_study.intent_superseded`
- `self_study.effective_policy_snapshotted`
- `self_study.resource_acquisition_preference_changed`
- `self_study.resource_acquisition_authorized`
- `self_study.resource_acquisition_rejected`
- `self_study.autonomous_fallback_authorized`
- `self_study.autonomous_fallback_rejected`

## Operational validation

```powershell
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py migrate
docker compose exec backend pytest apps/self_study/tests -q
docker compose exec backend pytest apps/academic_review/tests apps/users/tests apps/academic/tests -q
docker compose exec frontend npm run smoke:audit
docker compose exec frontend npm run smoke:audit:test
```
