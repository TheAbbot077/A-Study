# 43 - Assessment Review Platform

## Purpose

PI-5I introduces the Assessment Review Platform as the quality assurance layer for assessment assets and assessment performance.

The capability is separate from assessment delivery, grading, evidence integration, and remediation.

Its responsibility is to improve assessment quality through explicit review workflows, reviewer assignment, difficulty calibration, quality findings, and analytics.

---

## Scope

The platform provides:

* assessment review lifecycle management
* question review lifecycle management
* quality finding capture
* review decision capture
* reviewer assignment and reassignment
* rule-based difficulty calibration
* assessment review analytics
* event publication and event consumption hooks

The platform does not:

* deliver assessments
* grade responses
* create mastery decisions
* produce remediation plans
* generate questions
* call AI providers

---

## Canonical Models

### AssessmentReview

Represents quality review of an `Assessment`.

Fields include:

* assessment
* status
* opened_by
* reviewer
* opened_at
* started_at
* completed_at
* metadata

### QuestionReview

Represents quality review of an `ItemBankEntry`.

Fields mirror `AssessmentReview` but target reusable question-bank content.

### QualityFinding

Captures a review issue or observation linked to an assessment review or question review.

### ReviewDecision

Captures an explicit review outcome such as approved, needs revision, rejected, or archived.

### DifficultyCalibration

Records rule-based comparison between expected item difficulty and observed learner performance.

### ReviewerAssignment

Tracks who is assigned to a review, reassignment history, and completion state.

---

## Review Lifecycle

Supported review states:

* `draft`
* `pending_review`
* `in_review`
* `approved`
* `needs_revision`
* `rejected`
* `archived`

Allowed transitions:

* `draft -> pending_review`
* `draft -> archived`
* `pending_review -> in_review`
* `pending_review -> archived`
* `in_review -> approved`
* `in_review -> needs_revision`
* `in_review -> rejected`
* `in_review -> archived`
* `needs_revision -> pending_review`
* `needs_revision -> archived`
* `approved -> archived`
* `rejected -> archived`

This makes review workflow explicit and prevents silent state drift.

---

## Application Services

### AssessmentReviewService

Responsibilities:

* open assessment reviews
* start review work
* record findings
* record decisions
* publish review lifecycle events

### QuestionReviewService

Responsibilities:

* open question reviews
* record question-level findings
* record question review decisions
* publish question review events

### DifficultyCalibrationService

Responsibilities:

* compare expected difficulty with observed success rate
* store calibration history
* publish calibration events

### ReviewerAssignmentService

Responsibilities:

* assign reviewers
* reassign reviewers
* mark assignments complete
* report reviewer workload and history

### AssessmentAnalyticsService

Responsibilities:

* aggregate pass-rate and average-score data
* report question success rate where reachable
* expose review backlog and review cycle time
* expose approval and revision rates

---

## Calibration Rules

Initial calibration is deterministic.

Rules:

* insufficient sample size or missing success data keeps expected difficulty and marks the calibration as `insufficient_data`
* high learner success rate suggests the item is easier than expected
* low learner success rate suggests the item is harder than expected
* mid-range learner success rate keeps the expected difficulty

This policy is isolated so future calibration engines can replace it without rewriting surrounding services.

---

## Event Flow

Published events:

* `assessment_review.started`
* `assessment_review.question_reviewed`
* `assessment_review.difficulty_calibrated`
* `assessment_review.assessment_approved`
* `assessment_review.assessment_rejected`
* `assessment_review.assessment_needs_revision`

Consumed event hooks:

* `assessment.item_bank_entry_created`
* `assessment.attempt_evaluated`
* `assessment.evaluation_integrated_as_evidence`
* `assessment.result_integrated_as_evidence`
* `assessment.item_added_to_assessment`

Current subscribers are intentionally lightweight integration points. They reserve clean extension seams for automated review workflows without forcing policy into event adapters.

---

## Dependency Direction

The Assessment Review Platform depends on:

* PI-5A assessment structures
* PI-5D item bank content
* PI-5F evaluation outputs
* PI-5G integrated evidence events

It does not own delivery, grading, mastery, or remediation logic.

---

## API Surface

Primary REST resources:

* `/api/assessment-review/assessment-reviews/`
* `/api/assessment-review/question-reviews/`
* `/api/assessment-review/reviewer-assignments/`
* `/api/assessment-review/calibrations/`
* `/api/assessment-review/analytics/`

These endpoints support review creation, review retrieval, pending queues, review decisions, calibration submission, reviewer workload, and analytics retrieval.

---

## Admin Support

Django Admin provides management views for:

* assessment reviews
* question reviews
* quality findings
* review decisions
* difficulty calibrations
* reviewer assignments

This gives operators queue visibility before dedicated dashboards exist.

---

## Known Limitations

PI-5I does not yet implement:

* automated review generation
* AI-assisted calibration
* statistical discrimination metrics beyond placeholder reporting
* advanced reviewer capacity balancing
* dedicated published-assessment workflow state

These remain future extensions rather than concerns of the initial platform slice.
