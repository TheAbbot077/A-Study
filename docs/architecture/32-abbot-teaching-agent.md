# Abbot Teaching Agent

## Status

Implemented for PI-4F.

## Purpose

The Abbot Teaching Agent coordinates the completed PI-4 teaching pipeline and produces structured teaching responses without coupling the platform to an AI provider.

PI-4F uses a deterministic placeholder generator. The placeholder consumes grounded evidence and instructional strategy steps, preserves source references, and stores Abbot messages through the conversation/session layer.

## Scope

PI-4F implements:

* `AbbotTeachingRequest`
* `AbbotTeachingResponse`
* `AbbotResponseSection`
* `AbbotGenerationPlan`
* `AbbotTeachingAgentService`
* `learning.abbot_request_prepared`
* `learning.abbot_response_generated`
* `learning.abbot_response_validated`

## Service Boundary

`AbbotTeachingAgentService` coordinates:

* `ContextAssemblyService`
* `GroundingService`
* `InstructionalStrategyService`
* `ConversationOrchestratorService`
* `PedagogicalSessionService`

Service methods:

* `prepare_teaching_request(session)`
* `generate_teaching_response(session)`
* `generate_clarification_response(session, learner_question)`
* `generate_summary_response(session)`
* `validate_response(response)`

## Response Shape

`AbbotTeachingResponse` includes:

* session id
* concept title
* response type
* structured response sections
* source references
* strategy used
* metadata

Supported response types:

* `teaching`
* `clarification`
* `summary`
* `system`

## Deterministic Placeholder Generation

The placeholder generator:

* uses the Grounded Teaching Package
* uses Instructional Strategy steps
* emits structured response sections
* includes source references
* records that no AI provider was used
* avoids claims outside the grounded package and strategy

This is not prompt generation. It is a deterministic stand-in until a future provider integration layer is designed.

## Events

The service publishes:

* `learning.abbot_request_prepared`
* `learning.abbot_response_generated`
* `learning.abbot_response_validated`

## Architectural Boundaries

The Abbot Teaching Agent must not:

* change curriculum
* reorder content
* award mastery
* unlock concepts
* modify academic content
* bypass grounding
* call an AI provider directly

PI-4F does not implement:

* OpenAI, Anthropic, Gemini, or any real AI provider
* dynamic prompt generation
* assessment
* mastery
* learner progression
* Ariel teach-back

## Validation Commands

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py test apps.learning
```
