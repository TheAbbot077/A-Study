# Abbot Teaching Agent

## Status

Accepted

## Context

PI-4A through PI-4E created the teaching pipeline foundation: Pedagogical Sessions, Context Assembly, Grounding, Instructional Strategy, and Conversation Orchestration.

The pipeline now needs an Abbot Teaching Agent that coordinates those services and produces structured teaching responses. Provider integration remains out of scope, because AI providers must not define curriculum, grounding, strategy, mastery, or progression.

## Decision

We will implement the Abbot Teaching Agent in `apps.learning`.

The capability introduces immutable domain structures:

* `AbbotTeachingRequest`
* `AbbotTeachingResponse`
* `AbbotResponseSection`
* `AbbotGenerationPlan`

`AbbotTeachingAgentService` prepares teaching requests, generates deterministic placeholder teaching/clarification/summary responses, validates responses, and stores Abbot messages through the conversation/session layer.

The service publishes:

* `learning.abbot_request_prepared`
* `learning.abbot_response_generated`
* `learning.abbot_response_validated`

## Consequences

* The full PI-4 teaching pipeline can produce structured responses without an AI provider.
* Response generation remains source-aware and deterministic for now.
* Future provider integration can replace the placeholder generation boundary without changing upstream educational policy services.
* Abbot messages are recorded in Pedagogical Sessions through existing conversation infrastructure.

## Non-Goals

This ADR does not authorize:

* OpenAI, Anthropic, Gemini, or any real AI provider integration
* dynamic prompt generation
* assessment
* mastery
* learner progression
* Ariel teach-back
* academic content mutation
