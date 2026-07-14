# Evidence & Mastery Engine

## Status

Implemented for PI-5B.

## Purpose

The Evidence & Mastery Engine records evidence of learning and produces explicit mastery decisions for a learner and Content Concept.

PI-5B establishes mastery as a deterministic service-owned decision over historical evidence. It does not unlock content, advance learner progression, generate remediation, grade with complex algorithms, evaluate with AI, or generate questions.

## Scope

PI-5B implements:

* `LearningEvidence`
* `MasteryDecision`
* `MasteryProfile`
* `LearningEvidenceSourceType`
* `LearningEvidenceType`
* `MasteryDecisionValue`
* `EvidenceService`
* `MasteryService`

## Evidence Sources

Supported `source_type` values:

* `assessment_attempt`
* `assessment_result`
* `teach_back`
* `oral_response`
* `project`
* `simulation`
* `manual_review`
* `system`

Assessment is one evidence source. The platform is intentionally broader so future learning interactions can contribute evidence without bypassing the assessment foundation.

## Evidence Types

Supported `evidence_type` values:

* `correct_response`
* `partial_understanding`
* `misconception`
* `explanation_quality`
* `applied_reasoning`
* `completion`
* `manual_observation`
* `other`

## Mastery Decisions

Supported decision values:

* `not_enough_evidence`
* `not_mastered`
* `emerging`
* `mastered`
* `needs_review`

`MasteryDecision` is historical. `MasteryProfile` stores the current decision for the learner and Content Concept pair.

## Service Boundary

`EvidenceService` owns evidence recording and evidence listing.

Service methods:

* `record_evidence`
* `list_evidence_for_learner`
* `list_evidence_for_concept`
* `list_evidence_for_learner_concept`

`MasteryService` owns mastery evaluation, decision creation, and profile updates.

Service methods:

* `evaluate_mastery`
* `create_mastery_decision`
* `update_mastery_profile`
* `get_mastery_profile`
* `list_mastery_profiles_for_learner`

## Initial Deterministic Logic

The initial mastery logic is deliberately simple:

* no evidence produces `not_enough_evidence`
* high-confidence positive evidence can produce `mastered`
* high-confidence misconception evidence can produce `not_mastered`
* mixed positive and misconception evidence produces `needs_review`
* weaker evidence produces `emerging`

These rules are deterministic and only use existing `LearningEvidence` records.

## Constraints

The data model enforces:

* one `MasteryProfile` per learner and Content Concept
* confidence values between `0` and `1`
* nullable score values bounded between `0` and `1` when present

## Events

The services publish:

* `assessment.learning_evidence_recorded`
* `assessment.mastery_decision_created`
* `assessment.mastery_profile_updated`

## Architectural Boundaries

PI-5B does not include:

* sequential unlocking
* learner progression
* remediation
* complex grading algorithms
* AI evaluation
* question generation
* frontend UI

## Validation Commands

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py migrate
docker compose exec backend pytest apps/assessments
```
