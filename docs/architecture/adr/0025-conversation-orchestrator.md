# Conversation Orchestrator

## Status

Accepted

## Context

PI-4A created Pedagogical Sessions. PI-4B created Pedagogical Context. PI-4C created Grounded Teaching Packages. PI-4D created Instructional Strategies. The canonical teaching pipeline now needs a conversation layer that manages dialogue state without taking over instructional policy or AI provider responsibilities.

The Learning Philosophy treats questions, clarification, reflection, and active learner participation as core teaching behaviors. The orchestrator must support these interactions while remaining deterministic and independent of language generation.

## Decision

We will implement the Conversation Orchestrator in `apps.learning`.

The capability introduces immutable domain structures:

* `ConversationContext`
* `ConversationTurn`
* `ConversationWindow`

`ConversationOrchestratorService` will initialize conversation context, add ordered turns, calculate the next expected interaction, trim active windows, and list turns. Message persistence remains delegated to the Pedagogical Session Platform.

The service publishes:

* `learning.conversation_initialized`
* `learning.turn_added`
* `learning.window_trimmed`

## Consequences

* Dialogue state becomes a first-class learning capability.
* Conversation management remains separate from instructional strategy selection and AI language generation.
* Conversation windows can later support summarization without changing turn persistence.
* Downstream teaching agents can consume structured conversation state.

## Non-Goals

This ADR does not authorize:

* AI provider integration
* prompt generation
* lesson generation
* conversation summarization
* assessment
* learner progression
* instructional strategy mutation
