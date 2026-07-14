# Evaluation & Grading Platform

## Status

Implemented for PI-5F.

## Purpose

The Evaluation & Grading Platform evaluates submitted assessment responses and records explicit evaluation and result artifacts.

PI-5F is limited to deterministic grading and result aggregation. It does not create mastery decisions, update mastery profiles, unlock progression, trigger remediation, generate questions, call an AI provider, or create frontend UI.

## Scope

PI-5F implements:

* `AssessmentEvaluationService`
* explicit `AssessmentEvaluation` grading fields
* attempt-level `AssessmentResult` aggregate fields
* `EvaluatorType`
* deterministic grading for supported item types

## Deterministic Evaluation

The deterministic evaluator supports:

* `multiple_choice`
* `true_false`

The evaluator reads answer keys from `AssessmentItem.metadata` using one of:

* `answer_key`
* `correct_answer`
* `correct_option`
* `correct_value`

Learner responses are read from `AssessmentResponse.response_data` using one of:

* `answer`
* `selected_option`
* `selected`
* `value`

`matching` and `ordering` are not implemented in PI-5F because the current assessment item and item bank structures do not yet define a canonical answer-key shape for those item types.

## Evaluation Records

`AssessmentEvaluation` stores:

* response
* score
* max score
* correctness
* feedback
* evaluator type
* evaluation metadata
* timestamps

Supported evaluator types:

* `deterministic`
* `human`
* `ai`
* `system`

Only `deterministic` is implemented in PI-5F.

## Result Records

`AssessmentResult` stores attempt-level aggregate results:

* attempt
* total score
* max score
* percentage
* passed flag
* result metadata
* timestamps

The existing evaluation-level result relationship remains nullable for backward compatibility with the PI-5A foundation model.

## Service Boundary

`AssessmentEvaluationService` owns evaluation and grading mutations.

Service methods:

* `evaluate_response`
* `evaluate_attempt`
* `create_evaluation`
* `create_or_update_result`
* `list_evaluations_for_attempt`
* `get_result_for_attempt`

## Events

The service publishes:

* `assessment.response_evaluated`
* `assessment.attempt_evaluated`
* `assessment.result_created`
* `assessment.result_updated`

## Architectural Boundaries

PI-5F does not include:

* mastery decisions
* mastery profile updates
* sequential unlocking
* remediation
* AI grading
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
