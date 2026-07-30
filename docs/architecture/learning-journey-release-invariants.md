# Learning Journey Release Invariants

PI-8B.6 defines release invariants for the governed learning journey engine. These invariants are enforced through model immutability, service policy, operational integrity checks, and regression tests.

## Identity and authority

- A journey has one learner, one immutable journey type, one lifecycle state, and one authority provider.
- Self-study journeys are governed by self-study workspace authority.
- Institutional journeys are governed by institutional assignment authority.
- A learner cannot replace institutional curriculum authority through self-study intent.
- Authority conflicts are reported as integrity findings; recovery must not invent replacement authority.

## Source and subject binding

- Source bindings are immutable and unique by source.
- A journey may have only one active subject binding.
- Superseded subject bindings remain historical and do not govern new progression.
- Institutional subject authority uses `INSTITUTIONAL_ASSIGNMENT`; self-study subject authority uses governed curriculum resolution.

## Evidence, mastery, and progression

- Journey orchestration does not manufacture evidence.
- Mastery remains owned by the assessment/mastery bounded context.
- Competency progression derives from `MasteryDecision`, never from time, page views, or lesson completion.
- Repeated progression with unchanged mastery is idempotent.
- Remediation remains distinct from mastery and cannot silently lower curriculum requirements.

## Journey evolution and completion

- Journey synchronization reflects authoritative source state.
- Reads report freshness and do not create diagnostics, plans, mastery, interventions, or completion.
- Completion readiness depends on governed authority and competency policies.
- Institutional completion readiness is not certification, transcript generation, or grading.

## Operational safety

- Mutating actions require policy discovery, receipts, idempotency, and optimistic version control.
- Recovery repairs derived consistency only.
- Integrity checks are durable, deduplicated, and safe to run repeatedly.
- Batch operations are bounded and tenant-filterable.

