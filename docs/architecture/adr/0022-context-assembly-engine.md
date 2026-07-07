# Context Assembly Engine

## Status

Accepted

## Context

PI-4A created the canonical Pedagogical Session Platform. Future teaching capabilities need a stable context package that identifies the learner, the target Content Concept, and the reachable academic structure around that concept.

ASEM v2 requires domain-first implementation, service-owned business behavior, framework discovery bridges, and business event publication for meaningful actions.

The constitution requires source-grounded teaching and sequential learning, but PI-4B is not the point where grounding validation, prompt generation, lesson generation, assessment, or progression are implemented.

## Decision

We will implement the Context Assembly Engine inside `apps.learning`.

The capability introduces immutable snapshot data structures in `apps.learning.domain.models` and a `ContextAssemblyService` that assembles context from either:

* a `PedagogicalSession`
* a learner and `ContentConcept`

The assembled context captures concept, section, resource, subject, curriculum, curriculum unit, learner, session, review, quality, and metadata fields. Optional academic relationships remain nullable in the resulting snapshots.

The service publishes `learning.context_assembled` and registers the event with the EventRegistry.

## Consequences

* Future teaching orchestration can consume one stable context package.
* Academic content remains authoritative and unmutated by context assembly.
* Optional academic relationships do not block learning-context creation.
* Context assembly remains independent of AI providers, prompts, lessons, assessment, and progression.
* Event subscribers can later observe context assembly without changing the service contract.

## Non-Goals

This ADR does not authorize:

* AI provider integration
* prompt generation
* lesson generation
* grounding validation
* instructional strategy selection
* assessment behavior
* learner progression
* frontend UI
