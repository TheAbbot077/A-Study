# Assessment Foundation

## Status

Accepted

## Context

PI-4 completed the provider-agnostic Pedagogical Orchestration Platform. PI-5 begins Assessment & Mastery, but mastery decisions, grading, remediation, and progression require a canonical assessment substrate first.

ASEM v2 requires domain models to define business concepts, framework bridge modules to stay thin, business behavior to live in services, and meaningful actions to publish business events.

## Decision

We will implement PI-5A as a new `apps.assessments` capability.

The capability introduces:

* `Assessment`
* `AssessmentItem`
* `AssessmentAttempt`
* `AssessmentInteraction`
* `AssessmentResponse`
* `AssessmentEvaluation`
* `AssessmentResult`
* `AssessmentService`

`AssessmentService` owns creation, item addition, attempts, response submission, attempt completion, and listing behavior.

The service publishes:

* `assessment.created`
* `assessment.item_added`
* `assessment.attempt_started`
* `assessment.response_submitted`
* `assessment.attempt_completed`

## Consequences

* Future grading and mastery services have stable canonical records to consume.
* Assessment attempts and responses are captured before any scoring policy exists.
* The Assessment Foundation remains independent of AI generation and learner progression.
* PI-5 can evolve in small capabilities without redefining assessment identity or response storage.

## Non-Goals

This ADR does not authorize:

* grading
* mastery decisions
* question generation
* remediation
* learner progression
* AI integration
