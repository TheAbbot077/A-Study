# Pedagogical Session Platform

## Status

Implemented for PI-4A.

## Purpose

The Pedagogical Session Platform creates the canonical learning-interaction model for Abbot Study. It records a learner's structured teaching interaction for one Content Concept and the ordered messages exchanged during that interaction.

This capability is intentionally a foundation. It does not generate teaching content, assemble context, call AI providers, assess mastery, or advance learner progression.

## Scope

PI-4A implements:

* `PedagogicalSession`
* `PedagogicalMessage`
* `PedagogicalState`
* `PedagogicalSessionService`
* pedagogy business events
* database constraints for message ordering

## Domain Model

### PedagogicalSession

A PedagogicalSession is the persisted implementation of the canonical Teaching Session concept.

It belongs to:

* one learner
* one Content Concept

Supported statuses:

* `created`
* `active`
* `paused`
* `completed`
* `abandoned`

The model records `started_at`, nullable `ended_at`, `created_at`, and `updated_at`.

### PedagogicalMessage

A PedagogicalMessage is one ordered message in a PedagogicalSession.

Supported sender types:

* `learner`
* `abbot`
* `ariel`
* `system`

Supported message types:

* `explanation`
* `question`
* `response`
* `clarification`
* `summary`
* `system`

Messages are ordered by `sequence_number`. A session cannot contain duplicate sequence numbers, and sequence numbers must be greater than or equal to 1.

## Service Boundary

`PedagogicalSessionService` owns session lifecycle behavior and message creation.

Service methods:

* `create_session`
* `start_session`
* `pause_session`
* `resume_session`
* `complete_session`
* `abandon_session`
* `add_message`
* `list_messages`

Lifecycle transitions are explicit. Invalid transitions raise `ValueError` so callers cannot silently mutate session state outside the canonical flow.

## Events

The service publishes these business facts:

* `pedagogy.session_created`
* `pedagogy.session_started`
* `pedagogy.session_paused`
* `pedagogy.session_resumed`
* `pedagogy.session_completed`
* `pedagogy.session_abandoned`
* `pedagogy.message_added`

All event names are registered with the EventRegistry for discovery before subscribers exist.

## Architectural Boundaries

PI-4A depends on the Academic Domain only through `ContentConcept` and on Identity through the learner user reference.

PI-4A does not include:

* AI provider integration
* prompt management
* teaching context assembly
* lesson generation
* assessment behavior
* mastery decisions
* learner progression

Those capabilities remain future PI-4 or PI-5 work.

## Validation

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py test apps.learning
```
