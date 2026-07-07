# Instructional Strategy Engine

## Status

Implemented for PI-4D.

## Purpose

The Instructional Strategy Engine determines how a grounded concept should be taught before conversation orchestration or AI language generation occurs.

It consumes a `GroundedTeachingPackage` and produces a deterministic `StrategyRecommendation` containing an `InstructionalStrategy` and ordered `StrategyStep` records.

## Scope

PI-4D implements:

* `InstructionalStrategy`
* `StrategyStep`
* `StrategyRecommendation`
* `InstructionalStrategyService`
* deterministic rule-based strategy selection
* `learning.strategy_selected`
* `learning.strategy_validated`

## Built-In Strategies

The engine supports these canonical strategy identifiers:

* `direct_instruction` - Direct Instruction
* `worked_example` - Worked Example
* `guided_practice` - Guided Practice
* `socratic_dialogue` - Socratic Dialogue
* `analogy` - Analogy
* `visual_explanation` - Visual Explanation
* `concept_mapping` - Concept Mapping
* `problem_based_learning` - Problem-Based Learning

## Strategy Shape

Every `InstructionalStrategy` includes:

* strategy identifier
* human-readable name
* pedagogical objective
* ordered instructional steps
* estimated complexity
* metadata

Every `StrategyStep` includes:

* sequence number
* title
* instructional goal
* recommended interaction
* metadata

## Service Boundary

`InstructionalStrategyService` owns strategy selection, construction, validation, and step listing.

Service methods:

* `select_strategy(grounded_teaching_package)`
* `build_strategy(strategy_type, grounded_teaching_package)`
* `validate_strategy(strategy)`
* `list_strategy_steps(strategy)`

Selection is deterministic and rule-based. It uses only fields already present in the `GroundedTeachingPackage`, including grounding confidence, quality status, and supporting evidence types.

## Events

The service publishes:

* `learning.strategy_selected`
* `learning.strategy_validated`

## Architectural Boundaries

PI-4D does not include:

* AI provider integration
* prompt generation
* lesson generation
* conversation management
* assessment
* learner progression

The selected strategy describes pedagogical approach only. It does not create learner-facing instructional content.

## Validation Commands

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py test apps.learning
```
