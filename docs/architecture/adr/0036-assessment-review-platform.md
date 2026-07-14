# ADR 0036: Assessment Review Platform

## Status

Accepted.

## Context

PI-5A through PI-5H established assessment structure, delivery, evaluation, evidence integration, and remediation.

The platform still needed a dedicated quality capability for reviewing assessments and reusable question-bank items, tracking findings and review decisions, calibrating expected difficulty against observed learner performance, and exposing operational review analytics.

This capability must remain independent from assessment delivery and evidence production.

## Decision

Create a new `apps.assessment_review` capability.

Model quality assurance with:

* `AssessmentReview`
* `QuestionReview`
* `QualityFinding`
* `ReviewDecision`
* `DifficultyCalibration`
* `ReviewerAssignment`

Implement application services for:

* assessment reviews
* question reviews
* difficulty calibration
* reviewer assignment
* assessment review analytics

Use deterministic rule-based difficulty calibration in PI-5I.

Publish:

* `assessment_review.started`
* `assessment_review.question_reviewed`
* `assessment_review.difficulty_calibrated`
* `assessment_review.assessment_approved`
* `assessment_review.assessment_rejected`
* `assessment_review.assessment_needs_revision`

Subscribe to existing PI-5 events through the existing event platform rather than creating a parallel mechanism.

## Consequences

Assessment quality assurance becomes a first-class architectural capability rather than an admin-only concern.

Question review is separated from delivery and grading, which preserves clear platform boundaries.

Difficulty calibration history can evolve independently from grading and evidence logic.

Future AI-assisted review, calibration, and reviewer routing can be added by replacing policy implementations without rewriting persistence or lifecycle orchestration.

## Non-Goals

PI-5I does not implement:

* assessment delivery
* grading logic
* mastery decisions
* remediation planning
* AI review agents
* question generation
* frontend dashboards
