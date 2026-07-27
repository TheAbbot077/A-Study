# PI-7B.3 — Governed Declared Learning Identity Capture

PI-7B.3 integrates completed PI-7A conversational onboarding with Learning Identity.

The central invariant is:

> Onboarding may supply confirmed declarations, but Learning Identity decides how those declarations become durable, versioned, governed identity.

And:

> Conversation content is not identity merely because an AI can extract it.

## Ownership boundary

PI-7A owns onboarding state, learner responses, curriculum discovery, confirmation, selected curriculum, and onboarding lifecycle.

Learning Identity owns profile state, profile versions, controlled attributes, provenance, publication, restriction, and downstream-safe identity summaries.

The Learning Identity application layer consumes a typed source port, not Self Study ORM models. The concrete PI-7A adapter lives in infrastructure.

Infrastructure wiring helpers build preview/apply services with the real PI-7A adapter. Tests and future integrations can inject other implementations of the same port without changing application policy.

## Confirmed source contract

`ConfirmedOnboardingDeclarationSource` resolves a durable onboarding session and revision into a `ConfirmedLearningIdentityDeclarationSet`.

The resolver validates:

- onboarding exists;
- tenant and learner match;
- revision matches the durable onboarding version;
- onboarding is completed;
- confirmation timestamp is available.

It returns structured declarations only. It does not return transcripts, assistant messages, rejected curriculum candidates, resolver reasoning, or raw conversation snapshots.

## Supported mappings

The default `OnboardingDeclarationMappingRegistry` currently maps only structured PI-7A fields with clear PI-7B.1 equivalents:

- `topic_query` → `STUDY_GOAL`
- `qualification_query` → `TARGET_QUALIFICATION`
- `target_date` → `TARGET_EXAM_DATE`
- `weekly_study_minutes` → `WEEKLY_STUDY_CAPACITY`

Curriculum resolver metadata, selected-candidate scores, inferred level, conversation language, and rejected options are intentionally unsupported.

`TARGET_QUALIFICATION` remains a learner declaration. It is not official enrolment, institutional verification, or curriculum registration.

## Normalization and semantic comparison

Normalization is deterministic and type-specific:

- text values use bounded whitespace normalization;
- dates normalize to ISO date strings;
- weekly capacity normalizes to integer minutes per week.

Semantic comparison uses the same mapping policy as application. Equivalent representations do not create new profile versions.

Normalization may change representation, but it must not strengthen, infer, or reinterpret learner meaning.

## Synchronization receipts

`LearningIdentityDeclarationSynchronization` records each processed onboarding session/revision.

The receipt stores:

- tenant and learner;
- onboarding session and revision;
- source event identity;
- deterministic payload fingerprint;
- source schema version;
- status and result code;
- readiness status;
- safe change counts and reason codes;
- profile/profile-version references where applicable.

It does not store declaration values, study goals, accessibility values, transcripts, raw payloads, or assistant text.

Receipts begin with PI-7B.3. Existing declarations remain valid without backfilled receipts.

## Profile-version behavior

If no profile exists and at least one confirmed declaration is eligible, synchronization creates a profile and a draft version.

If an active profile exists, material changes create a new draft version. Unchanged current attributes are carried forward into independent rows. Compatible evidence links are cloned because PI-7B.2 evidence links are version-local through attributes.

Published versions are never mutated.

If an unrelated draft exists, synchronization blocks with `UNRELATED_DRAFT_EXISTS`.

## Publication policy

Automatic publication occurs only when provenance readiness is `READY`.

If readiness is `NEEDS_REVIEW` or `BLOCKED`, the synchronization receipt is blocked and the current published version is preserved.

Onboarding-derived attributes receive PI-7B.2 evidence links:

- source domain: `SELF_STUDY`
- source type: `ONBOARDING_CONTEXT`
- relationship: `SUPPORTS`
- authority: declarative

## Revision ordering and idempotency

Incoming onboarding revisions are processed monotonically per onboarding session.

- same revision + same fingerprint: idempotent replay;
- same revision + different fingerprint: `ONBOARDING_REVISION_PAYLOAD_CONFLICT`;
- older revision after newer receipt: `ONBOARDING_REVISION_STALE`;
- later revision: eligible for processing.

The fingerprint includes source identity, revision, tenant, learner, schema version, fields, normalized values, dispositions, and clearing markers. It excludes timestamps unrelated to meaning and database-generated IDs.

## Events

PI-7B.3 registers:

- `learning_identity.declarations.synchronized`
- `learning_identity.declaration.added`
- `learning_identity.declaration.updated`
- `learning_identity.declaration.cleared`
- `learning_identity.declaration.unchanged`
- `learning_identity.onboarding_sync.blocked`
- `learning_identity.onboarding_sync.failed`
- `learning_identity.profile_version.published_from_onboarding`

Events contain identifiers, status, change type, attribute type, restriction flag, and aggregate version. They do not contain declaration values, transcripts, raw learner responses, payload fingerprints, or restricted details.

## Deferred work

PI-7B.3 does not implement frontend editing, observed identity, derived guidance, diagnostic/assessment ingestion, correction workflows, or personalization policies.
