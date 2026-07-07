# Grounding Engine

## Status

Accepted

## Context

PI-4A introduced the Pedagogical Session Platform. PI-4B introduced the Context Assembly Engine. Future teaching orchestration needs a deterministic evidence package that identifies the primary concept and preserves source references before any prompt, lesson, or conversational behavior is introduced.

The constitution requires source-grounded teaching wherever possible. ASEM v2 requires business behavior in services, domain concepts in domain models, and meaningful business events for domain facts.

## Decision

We will implement the Grounding Engine in `apps.learning`.

The capability introduces immutable data structures for:

* `GroundedTeachingPackage`
* `PrimaryEvidence`
* `SupportingEvidence`
* `SourceReference`

`GroundingService` transforms `PedagogicalContext` into a deterministic `GroundedTeachingPackage`, validates that the package has minimum grounding structure, lists source references, and publishes:

* `learning.grounding_package_created`
* `learning.grounding_validated`

The service consumes context snapshots and does not mutate academic content.

## Consequences

* Future PI-4 teaching orchestration can consume a stable evidence package.
* Provenance is explicit before prompts or generated teaching content exist.
* Validation is structural only in PI-4C; deeper grounding quality checks remain future work.
* Grounding remains decoupled from LLM calls, lessons, strategies, conversation, assessment, and progression.

## Non-Goals

This ADR does not authorize:

* prompt generation
* lesson generation
* LLM integration
* instructional strategy selection
* conversation behavior
* assessment
* learner progression
