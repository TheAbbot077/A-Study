# Instructional Strategy Engine

## Status

Accepted

## Context

PI-4A created Pedagogical Sessions. PI-4B created Pedagogical Context. PI-4C created Grounded Teaching Packages. The canonical teaching pipeline now needs a deterministic way to choose an instructional approach before any conversation or AI language generation occurs.

The Learning Philosophy requires multiple instructional approaches while preserving source grounding, learner respect, and separation between educational policy and AI provider behavior.

## Decision

We will implement the Instructional Strategy Engine in `apps.learning`.

The capability introduces immutable domain structures:

* `InstructionalStrategy`
* `StrategyStep`
* `StrategyRecommendation`

`InstructionalStrategyService` will select and build strategies using only `GroundedTeachingPackage` data. Initial selection is deterministic and rule-based, not AI-driven.

The service publishes:

* `learning.strategy_selected`
* `learning.strategy_validated`

## Consequences

* Conversation and language-generation layers can consume a structured pedagogical approach.
* Strategy selection remains auditable and deterministic.
* The AI provider does not determine how a concept should be taught.
* Future capabilities can refine strategy rules without changing the pipeline boundary.

## Non-Goals

This ADR does not authorize:

* AI provider integration
* prompt generation
* lesson generation
* conversation management
* assessment
* learner progression
