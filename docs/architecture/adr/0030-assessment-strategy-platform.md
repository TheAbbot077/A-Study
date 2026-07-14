# ADR 0030: Assessment Strategy Platform

## Status

Accepted.

## Context

PI-5A created the Assessment Foundation. PI-5B broadened assessment into the Evidence of Learning Platform by recording evidence and deriving explicit mastery decisions.

PI-5C needs a deterministic layer that decides what kind of evidence should be collected next for a Content Concept. This decision must happen before item generation, grading, remediation, or learner progression.

## Decision

Implement assessment strategies and blueprints as immutable value objects:

* `AssessmentStrategy`
* `AssessmentStrategyStep`
* `AssessmentBlueprint`
* `AssessmentEvidenceRequirement`

Implement `AssessmentStrategyService` to select strategies, build blueprints, validate strategies, validate blueprints, and list supported strategies.

Use deterministic rule-based selection from the optional `MasteryProfile.current_decision`.

Register and publish:

* `assessment.strategy_selected`
* `assessment.blueprint_built`
* `assessment.strategy_validated`
* `assessment.blueprint_validated`

## Consequences

Assessment planning is separated from assessment item creation.

Future question generation can consume blueprints without owning mastery policy.

Future mastery and progression work can reason from explicit evidence requirements rather than inferred item choices.

No new migration is required because strategies and blueprints are not persisted in PI-5C.

## Non-Goals

PI-5C does not implement:

* question generation
* automatic `AssessmentItem` creation
* grading
* remediation
* unlocking or learner progression
* AI evaluation
* frontend UI
