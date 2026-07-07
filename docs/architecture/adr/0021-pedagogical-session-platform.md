# Pedagogical Session Platform

## Status

Accepted

## Context

PI-4 begins the Learning Engine. The constitution defines Teaching Sessions as the learner's interaction with The Abbot for one Content Concept, but assessment, progression, prompt orchestration, and AI provider integration are explicitly out of scope for PI-4A.

ASEM v2 requires business logic to live in services, domain models to define business concepts, Django `models.py` to remain a discovery bridge, and meaningful business actions to publish events.

The repository already contains a placeholder `apps.learning` package, making it the correct bounded context for the first PI-4 capability.

## Decision

We will implement PI-4A in `apps.learning` as the Pedagogical Session Platform.

The capability introduces:

* `PedagogicalSession` as the persisted Teaching Session record
* `PedagogicalMessage` as the ordered conversation/message log
* `PedagogicalState` as the canonical session status vocabulary
* `PedagogicalSessionService` as the only lifecycle/message mutation service
* `pedagogy.*` business events registered with the EventRegistry

`apps.learning.models` remains a Django discovery bridge that imports from `apps.learning.domain.models`.

The service allows explicit lifecycle transitions and rejects invalid transitions. It also validates message sequence numbers before persistence while the database enforces uniqueness and minimum sequence constraints.

## Consequences

* Future PI-4 capabilities have a stable canonical session substrate.
* Teaching interactions can be recorded without coupling to prompts, AI providers, assessment, or progression.
* Message order is deterministic through `sequence_number`.
* Event subscribers can be attached later without changing the service contract.
* The Learning Engine now depends on Academic Content Concepts but does not alter Academic Domain rules.

## Non-Goals

This ADR does not authorize:

* AI provider integration
* prompt implementation
* lesson generation
* teaching context assembly
* assessment
* mastery decisions
* learner progression
