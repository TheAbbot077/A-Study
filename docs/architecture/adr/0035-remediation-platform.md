# ADR 0035: Remediation Platform

## Status

Accepted.

## Context

PI-5G converts evaluated assessment artifacts into canonical `LearningEvidence`.

Remediation must consume evidence, not assessment-specific artifacts, because future evidence producers include Ariel teach-back, oral examinations, programming exercises, projects, clinical observations, simulations, and manual educator review.

## Decision

Create a new `apps.remediation` capability.

Model remediation with:

* `RemediationPlan`
* `RemediationRecommendation`
* `RemediationActivity`
* `RemediationAttempt`
* `RemediationOutcome`

Use repository contracts and Django persistence adapters.

Use policy objects and a policy registry for recommendation generation.

Keep execution services responsible only for remediation lifecycle coordination, not instructional activity execution.

Publish:

* `remediation.planned`
* `remediation.started`
* `remediation.completed`
* `remediation.escalated`
* `remediation.cancelled`
* `remediation.closed`

## Consequences

Remediation remains generic and evidence-oriented.

Assessment remains one evidence producer rather than the remediation owner.

Future policy engines can replace or extend rule-based recommendation policy without changing plan lifecycle or persistence.

## Non-Goals

PI-5H does not implement:

* sequential unlocking
* learner progression
* AI remediation generation
* instructional activity execution
* assessment-specific remediation assumptions
* frontend UI
