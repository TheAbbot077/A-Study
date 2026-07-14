# ADR 0029: Evidence & Mastery Engine

## Status

Accepted.

## Context

PI-5A created the Assessment Foundation but intentionally did not grade, award mastery, remediate, or unlock progression. PI-5B needs a canonical way to record evidence of learning and derive explicit mastery decisions without assuming assessment is the only evidence source.

The platform must support future evidence sources such as teach-back, oral responses, projects, simulations, and manual review while preserving a deterministic, auditable decision trail.

## Decision

Add `LearningEvidence`, `MasteryDecision`, and `MasteryProfile` to the assessments capability.

Use `EvidenceService` for evidence recording and listing.

Use `MasteryService` for deterministic mastery evaluation, mastery decision creation, and mastery profile updates.

Register and publish:

* `assessment.learning_evidence_recorded`
* `assessment.mastery_decision_created`
* `assessment.mastery_profile_updated`

Represent `MasteryDecision` as historical and `MasteryProfile` as the current learner/concept state.

## Consequences

Assessment becomes one input to a broader Evidence of Learning Platform instead of the only path to mastery.

Mastery state is auditable because every current profile is derived from an explicit decision record.

Future PI-5 capabilities can add richer grading, remediation, and progression without changing the canonical evidence and decision substrate.

## Non-Goals

PI-5B does not implement:

* sequential unlocking
* learner progression
* remediation
* complex grading algorithms
* AI evaluation
* question generation
* frontend UI
