# PI-7B.1 — Governed Learning Identity Core

PI-7B.1 introduces a dedicated backend bounded context for a learner’s governed academic identity. The context lives in `apps.learning_identity` and is intentionally separate from self-study, learning, assessment, academic curriculum, and authentication.

Learning Identity is a versioned representation of learner context. It is not a mutable biography, a psychological profile, a mastery record, or a substitute for academic evidence.

## Bounded context

The aggregate root is `LearnerLearningProfile`. A profile belongs to one tenant and one learner, and the database enforces at most one non-archived profile for that learner within that tenant.

The app contains:

- domain enums, validators, and Django-backed domain models;
- application services for lifecycle commands;
- an internal learner-safe summary query;
- admin inspection;
- migrations and focused tests.

No public API or frontend behavior is introduced in PI-7B.1.

## Versioning model

`LearningProfileVersion` stores immutable profile snapshots.

Supported states are:

- `DRAFT`
- `PUBLISHED`
- `SUPERSEDED`
- `REVOKED`

Publishing a draft atomically makes it the profile’s current version and supersedes the prior current published version. Published and superseded versions are preserved as history. Later correction workflows are intentionally deferred.

## Attribute model

`LearningIdentityAttribute` stores controlled identity attributes within a profile version.

Initial attribute vocabulary:

- `PREFERRED_LEARNING_LANGUAGE`
- `TARGET_QUALIFICATION`
- `TARGET_EXAM_DATE`
- `WEEKLY_STUDY_CAPACITY`
- `PRIOR_STUDY_EXPERIENCE`
- `ACCESSIBILITY_PREFERENCE`
- `STUDY_GOAL`
- `PREFERRED_EXPLANATION_FORMAT`
- `PACING_SUPPORT_PREFERENCE`

Arbitrary learner-defined keys are not accepted. Harmful profile vocabulary such as intelligence labels, fixed learning styles, disability inference, slow-learner labels, personality types, and risk rankings is excluded.

## Classification and provenance

Attributes support these classifications:

- `DECLARED`
- `VERIFIED`
- `OBSERVED`
- `DERIVED`

PI-7B.1 only provides a public application command for declared attributes. Non-declared classifications are modeled for future capabilities but require provenance metadata, and observed/derived attributes require confidence.

Source types include learner, authorized actor, institution, onboarding, diagnostic, assessment, learning session, and system derivation. PI-7B.1 does not yet attach cross-domain evidence records or ingest onboarding automatically.

## Privacy and visibility

Attributes preserve visibility:

- `LEARNER_VISIBLE`
- `AUTHORIZED_STAFF`
- `RESTRICTED`
- `SYSTEM_ONLY`

Restricted attributes cannot be learner-visible. The learner-safe summary query only emits learner-visible, unrestricted attributes, with safe labels and summaries rather than raw internal metadata.

## Lifecycle

Application services provide:

- create profile;
- create draft version;
- add declared attribute;
- publish profile version;
- restrict profile;
- archive profile.

State-changing commands enforce tenant membership, learner ownership or institutional authority, expected aggregate versions, and idempotency where applicable.

## Events

The following events are registered:

- `learning_identity.profile.created`
- `learning_identity.profile_version.created`
- `learning_identity.attribute.declared`
- `learning_identity.profile_version.published`
- `learning_identity.profile_version.superseded`
- `learning_identity.profile.restricted`
- `learning_identity.profile.archived`

Payloads contain identifiers and lifecycle metadata only. They do not include full profile snapshots, restricted values, medical or accessibility details, or framework model instances. Events are scheduled after transaction commit.

## Non-goals

PI-7B.1 does not:

- implement frontend behavior;
- expose public REST or GraphQL APIs;
- import PI-7A onboarding data automatically;
- ingest diagnostic or assessment evidence;
- infer mastery;
- create curriculum records or academic subjects;
- update self-study intent;
- generate AI profile summaries;
- create purpose-limited downstream projections.

PI-7B.2 is expected to deepen provenance and evidence linkage. PI-7B.3 is expected to integrate conversational onboarding declarations.

## Manual validation

The human operator should run Docker validation after review:

```powershell
docker compose exec backend pytest apps/learning_identity
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py migrate
.\scripts\validate_backend.ps1
```
