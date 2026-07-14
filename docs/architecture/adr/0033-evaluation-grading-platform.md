# ADR 0033: Evaluation & Grading Platform

## Status

Accepted.

## Context

PI-5A introduced `AssessmentEvaluation` and `AssessmentResult` as foundation records without grading behavior. PI-5E introduced delivery and response submission.

PI-5F needs explicit evaluation and result artifacts while preserving the existing assessment foundation model.

## Decision

Extend the existing `AssessmentEvaluation` model with explicit grading fields:

* score
* max score
* correctness
* feedback
* evaluator type

Extend the existing `AssessmentResult` model with attempt-level aggregate fields:

* attempt
* total score
* max score
* percentage
* passed flag

Implement `AssessmentEvaluationService` for deterministic response evaluation, attempt evaluation, result creation/update, and evaluation/result queries.

Support deterministic grading for `multiple_choice` and `true_false` when an answer key exists in assessment item metadata.

Register and publish:

* `assessment.response_evaluated`
* `assessment.attempt_evaluated`
* `assessment.result_created`
* `assessment.result_updated`

## Consequences

Evaluation and result state remain canonical rather than duplicated in a parallel grading model.

Attempt-level result aggregation is now available for future evidence generation, while PI-5F still does not update mastery.

Matching and ordering grading remain deferred until their answer-key shape is defined.

## Non-Goals

PI-5F does not implement:

* mastery decisions
* mastery profile updates
* sequential unlocking
* remediation
* AI grading
* question generation
* frontend UI
