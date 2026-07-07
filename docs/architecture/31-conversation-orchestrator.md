# Conversation Orchestrator

## Status

Implemented for PI-4E.

## Purpose

The Conversation Orchestrator manages pedagogical dialogue state after instructional strategy selection and before any teaching agent or AI provider generates language.

It preserves turn order, tracks the active conversation window, and determines the next expected interaction type without defining instructional policy or generating content.

## Scope

PI-4E implements:

* `ConversationContext`
* `ConversationTurn`
* `ConversationWindow`
* `ConversationOrchestratorService`
* `learning.conversation_initialized`
* `learning.turn_added`
* `learning.window_trimmed`

## Conversation Structures

### ConversationContext

Includes:

* pedagogical session
* grounded teaching package reference
* instructional strategy reference
* active conversation window
* current turn number
* current instructional step
* metadata

### ConversationTurn

Includes:

* sequence number
* sender type
* message type
* content
* timestamp
* metadata

### ConversationWindow

Preserves chronological order and exposes a configurable window size.

The window includes `supports_future_summarization` metadata, but PI-4E does not implement summarization.

## Supported Interaction Types

The orchestrator recognizes:

* `explanation`
* `learner_question`
* `clarification`
* `acknowledgement`
* `reflection`
* `summary`
* `transition`
* `system`

## Service Boundary

`ConversationOrchestratorService` owns conversation initialization, turn creation, turn listing, active-window trimming, and next-interaction calculation.

Service methods:

* `initialize_conversation(session)`
* `build_conversation_context(session)`
* `add_turn(session, sender_type, message_type, content)`
* `next_expected_interaction(session)`
* `trim_conversation_window(session, max_turns=None)`
* `list_conversation_turns(session)`

The orchestrator delegates message persistence to the Pedagogical Session Platform. It consumes context, grounding, and strategy outputs but does not modify them.

## Events

The service publishes:

* `learning.conversation_initialized`
* `learning.turn_added`
* `learning.window_trimmed`

## Architectural Boundaries

PI-4E does not include:

* AI provider integration
* prompt generation
* lesson generation
* conversation summarization
* assessment
* learner progression
* instructional strategy mutation

The orchestrator manages dialogue structure only.

## Validation Commands

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py test apps.learning
```
