# ADR 0032: Assessment Delivery Engine

## Status

Accepted.

## Context

PI-5A established assessment attempts and responses. PI-5D established reusable item bank entries and assessment links.

PI-5E needs a delivery layer that can track a learner's active assessment experience, preserve item order, submit responses, and complete or abandon delivery without grading or mastery decisions.

`AssessmentAttempt` already records assessment participation, but it does not carry delivery cursor state such as current sequence number, pause state, or abandoned delivery.

## Decision

Add `AssessmentDeliverySession` as a persisted delivery cursor and lifecycle record.

Add `AssessmentDeliveryItem` as a value object that wraps either an `AssessmentItemBankLink` or direct `AssessmentItem` in sequence order.

Implement `AssessmentDeliveryService` as the business boundary for creating delivery sessions, starting delivery, presenting items, moving the cursor, submitting responses, and ending delivery.

Use `AssessmentResponse` when a delivered item is backed by an `AssessmentItem`. Defer item-bank-only response persistence until a later capability defines item materialization or a response target for `ItemBankEntry`.

Register and publish:

* `assessment.delivery_session_created`
* `assessment.delivery_session_started`
* `assessment.delivery_item_presented`
* `assessment.delivery_response_submitted`
* `assessment.delivery_session_submitted`
* `assessment.delivery_session_completed`
* `assessment.delivery_session_abandoned`

## Consequences

Delivery state is explicit and separate from assessment authoring, grading, mastery, and progression.

Existing foundation assessments using `AssessmentItem` can submit `AssessmentResponse` records immediately.

Item bank delivery can preserve order and presentation now, while response persistence for item-bank-only flows remains a conscious future design decision.

## Non-Goals

PI-5E does not implement:

* grading
* mastery decisions
* remediation
* unlocking or learner progression
* AI generation
* frontend UI
* advanced timing or proctoring
