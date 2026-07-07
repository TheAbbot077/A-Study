# Learning Companion Platform

## Status

Implemented for PI-4G.

## Purpose

The Learning Companion Platform provides reusable companion architecture for non-primary teaching support within Abbot Study.

A companion can encourage, prompt reflection, maintain presence, and support session continuity, but it does not replace The Abbot, assess mastery, unlock progression, or alter curriculum.

Ariel is the first concrete companion implementation.

## Scope

PI-4G implements:

* `LearningCompanion`
* `CompanionProfile`
* `CompanionInteraction`
* `CompanionResponse`
* `ArielCompanion`
* `LearningCompanionService`
* `learning.companion_registered`
* `learning.companion_activated`
* `learning.companion_deactivated`
* `learning.companion_response_generated`

## Supported Companion Types

* `ariel`
* `debate_partner`
* `lab_assistant`
* `language_partner`
* `interview_panelist`
* `study_buddy`
* `system`

## Supported Interaction Types

* `presence`
* `encouragement`
* `reflection_prompt`
* `clarification_prompt`
* `learning_check`
* `session_summary`
* `system`

## Ariel Companion

Ariel is deterministic in PI-4G.

Ariel supports:

* presence
* encouragement
* reflection prompt
* session summary

Ariel does not implement teach-back mastery, assessment, progression, voice, avatar UI, or dynamic prompts.

## Service Boundary

`LearningCompanionService` owns companion registration, retrieval, session activation, session deactivation, response generation, and session companion listing.

Service methods:

* `register_companion`
* `get_companion`
* `list_companions`
* `activate_companion_for_session`
* `deactivate_companion_for_session`
* `generate_companion_response`
* `list_session_companions`

Companion responses are recorded through the existing conversation/session infrastructure where appropriate.

## Events

The service publishes:

* `learning.companion_registered`
* `learning.companion_activated`
* `learning.companion_deactivated`
* `learning.companion_response_generated`

## Architectural Boundaries

Companion behavior must not:

* teach primary content instead of The Abbot
* assess mastery
* unlock concepts
* reorder curriculum
* modify academic content
* override instructional strategy
* bypass grounding

PI-4G does not include:

* Ariel teach-back mastery
* assessment
* learner progression
* AI provider integration
* voice or avatar UI
* Prep Season
* dynamic prompt generation

## Validation Commands

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py test apps.learning
```
