# Assessment Foundation

## Status

Implemented for PI-5A.

## Purpose

The Assessment Foundation creates the canonical assessment substrate used by future assessment types, mastery decisions, remediation, and progression workflows.

PI-5A defines assessment structure and service-owned lifecycle behavior. It does not grade responses, award mastery, generate questions, remediate learners, unlock content, or integrate AI.

## Scope

PI-5A implements:

* `Assessment`
* `AssessmentItem`
* `AssessmentAttempt`
* `AssessmentInteraction`
* `AssessmentResponse`
* `AssessmentEvaluation`
* `AssessmentResult`
* `AssessmentState`
* `AssessmentItemType`
* `AssessmentService`

## Assessment State

Supported assessment states:

* `created`
* `active`
* `submitted`
* `evaluated`
* `completed`
* `cancelled`

## Assessment Item Types

Supported item types:

* `multiple_choice`
* `short_answer`
* `essay`
* `calculation`
* `matching`
* `ordering`
* `true_false`
* `diagram`
* `oral`
* `teach_back`
* `programming`
* `clinical`
* `interview`
* `other`

## Relationships

```text
Assessment
  -> AssessmentItems
  -> AssessmentAttempts

AssessmentAttempt
  -> AssessmentResponses

AssessmentResponse
  -> AssessmentEvaluation

AssessmentEvaluation
  -> AssessmentResult
```

## Service Boundary

`AssessmentService` owns assessment mutations.

Service methods:

* `create_assessment`
* `add_item`
* `start_attempt`
* `submit_response`
* `complete_attempt`
* `list_attempts`
* `list_items`

Future grading and mastery services may consume these records but should not bypass this foundation.

## Events

The service publishes:

* `assessment.created`
* `assessment.item_added`
* `assessment.attempt_started`
* `assessment.response_submitted`
* `assessment.attempt_completed`

## Architectural Boundaries

PI-5A does not include:

* grading
* mastery
* question generation
* remediation
* learner progression
* AI integration

## Validation Commands

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py migrate
docker compose exec backend pytest apps/assessments
```
