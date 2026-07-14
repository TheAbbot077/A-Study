# Assessment Strategy Platform

## Status

Implemented for PI-5C.

## Purpose

The Assessment Strategy Platform determines what type of assessment evidence should be collected for a Content Concept before any assessment items are created.

PI-5C creates deterministic strategy and blueprint value objects. It does not generate questions, create `AssessmentItem` records, grade responses, remediate learners, unlock progression, or evaluate with AI.

## Scope

PI-5C implements:

* `AssessmentStrategy`
* `AssessmentStrategyStep`
* `AssessmentBlueprint`
* `AssessmentEvidenceRequirement`
* `AssessmentStrategyType`
* `AssessmentStrategyService`

These structures are value objects, not persisted models. Persistence is deferred until a later capability has a clear operational need for stored strategy history or author-managed strategy catalogs.

## Supported Strategy Types

Supported `strategy_type` values:

* `concept_check`
* `knowledge_recall`
* `worked_problem`
* `applied_reasoning`
* `calculation_practice`
* `reflective_explanation`
* `teach_back_preparation`
* `oral_probe`
* `mixed_evidence`
* `review_check`

## Strategy Structure

`AssessmentStrategy` includes:

* strategy type
* name
* objective
* recommended item types
* evidence requirements
* ordered steps
* estimated difficulty
* metadata

`AssessmentStrategyStep` includes:

* sequence number
* title
* goal
* recommended item type
* metadata

`AssessmentEvidenceRequirement` includes:

* evidence type
* minimum confidence
* required flag
* metadata

## Blueprint Structure

`AssessmentBlueprint` includes:

* Content Concept id
* Content Concept title
* selected strategy
* recommended item count
* allowed item types
* mastery signal
* metadata

Blueprints are planning artifacts. They do not create assessment items.

## Deterministic Selection

Initial strategy selection is rule-based:

* no mastery profile selects `concept_check`
* `not_enough_evidence` selects `concept_check`
* `emerging` selects `worked_problem`
* `not_mastered` selects `review_check`
* `needs_review` selects `mixed_evidence`
* `mastered` selects `review_check`

The service only uses the provided Content Concept, optional Mastery Profile, and optional context metadata.

## Service Boundary

`AssessmentStrategyService` owns assessment strategy selection, blueprint construction, and validation.

Service methods:

* `select_strategy`
* `build_blueprint`
* `validate_strategy`
* `validate_blueprint`
* `list_supported_strategies`

The service must not mutate academic content or mastery profiles.

## Events

The service publishes:

* `assessment.strategy_selected`
* `assessment.blueprint_built`
* `assessment.strategy_validated`
* `assessment.blueprint_validated`

## Architectural Boundaries

PI-5C does not include:

* question generation
* automatic `AssessmentItem` creation
* grading
* remediation
* unlocking or learner progression
* AI evaluation
* frontend UI

## Validation Commands

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py migrate
docker compose exec backend pytest apps/assessments
```
