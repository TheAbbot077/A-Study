# Context Assembly Engine

## Status

Implemented for PI-4B.

## Purpose

The Context Assembly Engine produces a stable pedagogical context package for a PedagogicalSession or for a learner and Content Concept pair.

It is a read-only learning capability. It gathers the canonical academic details needed by future teaching orchestration without mutating academic content and without invoking AI.

## Scope

PI-4B implements:

* `PedagogicalContext`
* `ContextConceptSnapshot`
* `ContextSectionSnapshot`
* `ContextResourceSnapshot`
* `ContextCurriculumSnapshot`
* `ContextLearnerSnapshot`
* `ContextAssemblyService`
* `learning.context_assembled`

## Context Shape

The assembled context includes:

* session id when assembled from a session
* learner id
* content concept id
* content concept title
* content concept description
* content concept learning objective
* content section id
* content section title
* learning resource id
* learning resource title
* resource type
* subject id and name when reachable
* curriculum id and name when reachable
* curriculum unit id and title when reachable
* review status and quality status where available
* metadata

## Service Boundary

`ContextAssemblyService` owns context assembly.

Service methods:

* `assemble_for_session(session)`
* `assemble_for_concept(learner, content_concept)`

The service traverses existing academic relationships:

`ContentConcept -> ContentSection -> LearningResource -> Subject/Curriculum/CurriculumUnit`

The service tolerates nullable optional relationships. Missing curriculum, curriculum unit, institution, or session context is represented with `None` values rather than errors.

## Events

The service publishes:

* `learning.context_assembled`

The event is a business fact that a context package was assembled. It does not imply that teaching occurred, AI was called, assessment was started, or progression changed.

## Architectural Boundaries

PI-4B does not include:

* AI provider integration
* prompt generation
* lesson generation
* grounding validation
* instructional strategy selection
* assessment
* mastery decisions
* learner progression
* frontend UI

Future PI-4 capabilities may consume this context package when they implement orchestration, grounding, and conversational teaching.

## Validation

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py test apps.learning
```
