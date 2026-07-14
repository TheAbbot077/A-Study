# Evidence Integration Platform

## Status

Implemented for PI-5G.

## Purpose

The Evidence Integration Platform converts evaluated assessment artifacts into canonical `LearningEvidence`.

PI-5G connects the Evaluation & Grading Platform to the broader Evidence of Learning Platform. It does not update mastery automatically, unlock progression, trigger remediation, generate questions, call AI, or mutate academic content.

## Scope

PI-5G implements:

* `EvidenceIntegrationService`
* `EvidenceIntegrationSummary`
* evaluation-to-evidence mapping
* result-to-evidence mapping
* service-level idempotency safeguards
* assessment evidence provenance

## Integration Sources

Supported integration sources:

* `AssessmentEvaluation`
* `AssessmentResult`
* `AssessmentAttempt` as an integration boundary over associated evaluations and result

`assessment_evaluation` is added as a `LearningEvidenceSourceType` so evaluation provenance can be represented directly.

## Evidence Mapping

Evaluation mapping:

* correct response maps to `correct_response`
* partial score maps to `partial_understanding`
* incorrect response maps to `misconception`
* confidence is derived deterministically from `score / max_score`

Result mapping:

* passed or high percentage maps to `completion`
* mid-range percentage maps to `partial_understanding`
* low failed percentage maps to `misconception`
* confidence is derived deterministically from percentage

## Idempotency

The service checks for existing `LearningEvidence` with the same `source_type` and `source_id` before recording new evidence.

This is a service-level safeguard because the current `LearningEvidence` model does not enforce source uniqueness in the database.

## Service Boundary

`EvidenceIntegrationService` owns conversion from evaluated assessment artifacts into `LearningEvidence`.

Service methods:

* `integrate_evaluation`
* `integrate_result`
* `integrate_attempt`
* `integrate_completed_attempt`
* `list_integrated_evidence_for_attempt`

`integrate_completed_attempt` accepts submitted, evaluated, or completed attempts according to current assessment state conventions.

The service returns an `EvidenceIntegrationSummary` indicating that mastery may be reevaluated later, but it does not call `MasteryService`.

## Events

The service publishes:

* `assessment.evaluation_integrated_as_evidence`
* `assessment.result_integrated_as_evidence`
* `assessment.attempt_integrated_as_evidence`

## Architectural Boundaries

PI-5G does not include:

* mastery profile updates
* mastery decision creation
* sequential unlocking
* learner progression
* remediation
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
