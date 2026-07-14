# ADR 0034: Evidence Integration Platform

## Status

Accepted.

## Context

PI-5B introduced canonical `LearningEvidence`, `MasteryDecision`, and `MasteryProfile`.

PI-5F introduced explicit `AssessmentEvaluation` and `AssessmentResult` artifacts. These evaluated artifacts need to become evidence without making grading responsible for mastery or progression.

## Decision

Implement `EvidenceIntegrationService` to convert assessment evaluations and results into `LearningEvidence`.

Use `assessment_evaluation` and `assessment_result` source types to preserve provenance.

Implement service-level idempotency by checking for existing evidence with the same `source_type` and `source_id`.

Return an `EvidenceIntegrationSummary` that indicates mastery reevaluation may be appropriate later, but do not automatically update mastery in PI-5G.

Register and publish:

* `assessment.evaluation_integrated_as_evidence`
* `assessment.result_integrated_as_evidence`
* `assessment.attempt_integrated_as_evidence`

## Consequences

Evaluation and grading remain separate from mastery decisions.

Assessment artifacts can now contribute to the Evidence of Learning Platform through canonical `LearningEvidence`.

Future mastery workflows can consume integrated evidence explicitly instead of depending on grading side effects.

## Non-Goals

PI-5G does not implement:

* mastery decisions
* mastery profile updates
* sequential unlocking
* learner progression
* remediation
* AI evaluation
* question generation
* frontend UI
