# Learning Companion Platform

## Status

Accepted

## Context

PI-4A through PI-4F created the main teaching pipeline and Abbot orchestration layer. The product also needs companions that can support presence, encouragement, reflection, and session continuity without taking over The Abbot's teaching authority.

Ariel is a named learning companion in the Learning Philosophy, but companion architecture should be reusable for future roles such as debate partners, lab assistants, language partners, interview panelists, and study buddies.

## Decision

We will implement the Learning Companion Platform in `apps.learning`.

The capability introduces immutable domain structures:

* `LearningCompanion`
* `CompanionProfile`
* `CompanionInteraction`
* `CompanionResponse`
* `ArielCompanion`

`LearningCompanionService` provides registration, retrieval, listing, session activation, session deactivation, deterministic response generation, and session companion listing.

Ariel is registered as the first default companion and provides deterministic responses for presence, encouragement, reflection prompts, and session summaries.

The service publishes:

* `learning.companion_registered`
* `learning.companion_activated`
* `learning.companion_deactivated`
* `learning.companion_response_generated`

## Consequences

* Companion behavior becomes reusable rather than Ariel-specific.
* Ariel can participate in sessions without teaching primary content or making mastery decisions.
* Companion turns are recorded through existing conversation/session infrastructure.
* Future companions can be registered without changing the Abbot Teaching Agent.

## Non-Goals

This ADR does not authorize:

* Ariel teach-back mastery
* assessment
* learner progression
* AI provider integration
* voice or avatar UI
* Prep Season
* dynamic prompt generation
* academic content mutation
