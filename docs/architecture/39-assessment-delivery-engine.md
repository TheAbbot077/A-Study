# Assessment Delivery Engine

## Status

Implemented for PI-5E.

## Purpose

The Assessment Delivery Engine coordinates learner assessment attempts, item sequencing, and learner response submission.

PI-5E is delivery orchestration only. It does not grade responses, create mastery decisions, remediate learners, unlock progression, generate questions, or implement advanced timing or proctoring.

## Scope

PI-5E implements:

* `AssessmentDeliverySession`
* `AssessmentDeliveryItem`
* `AssessmentDeliveryState`
* `AssessmentDeliveryService`

## Delivery Session

`AssessmentDeliverySession` represents a learner's active delivery experience for an `Assessment`.

It includes:

* assessment
* learner
* optional linked assessment attempt
* status
* current sequence number
* started timestamp
* submitted timestamp
* completed timestamp
* metadata
* audit timestamps

Supported status values:

* `created`
* `active`
* `paused`
* `submitted`
* `completed`
* `abandoned`

## Delivery Items

`AssessmentDeliveryItem` is a value object that represents the next item to present.

Delivery items preserve sequence order from:

* `AssessmentItemBankLink.sequence_number` when item bank links exist
* `AssessmentItem.sequence_number` otherwise

PI-5E prefers item bank links when they are present. Direct `AssessmentItem` records remain supported for foundation-era assessments.

## Service Boundary

`AssessmentDeliveryService` owns delivery orchestration.

Service methods:

* `create_delivery_session`
* `start_delivery_session`
* `get_current_item`
* `move_to_next_item`
* `submit_response`
* `submit_delivery_session`
* `complete_delivery_session`
* `abandon_delivery_session`
* `list_delivery_items`
* `list_delivery_sessions_for_learner`

`submit_response` records `AssessmentResponse` when the delivered item is backed by an `AssessmentItem`. Item-bank-only response persistence is intentionally deferred until the platform defines an explicit item materialization or response target policy.

## Events

The service publishes:

* `assessment.delivery_session_created`
* `assessment.delivery_session_started`
* `assessment.delivery_item_presented`
* `assessment.delivery_response_submitted`
* `assessment.delivery_session_submitted`
* `assessment.delivery_session_completed`
* `assessment.delivery_session_abandoned`

## Architectural Boundaries

PI-5E does not include:

* grading
* mastery decisions
* remediation
* unlocking or learner progression
* AI generation
* frontend UI
* advanced timing or proctoring

The service must not mutate item bank entries, assessment item content, academic content, mastery profiles, or progression state.

## Validation Commands

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py migrate
docker compose exec backend pytest apps/assessments
```
