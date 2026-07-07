# Grounding Engine

## Status

Implemented for PI-4C.

## Purpose

The Grounding Engine transforms a canonical `PedagogicalContext` into a `GroundedTeachingPackage` containing authoritative instructional evidence and source provenance.

It prepares the evidence layer future teaching orchestration will consume. It does not generate prompts, lessons, conversations, assessments, or learner progression.

## Scope

PI-4C implements:

* `GroundedTeachingPackage`
* `PrimaryEvidence`
* `SupportingEvidence`
* `SourceReference`
* `GroundingService`
* `learning.grounding_package_created`
* `learning.grounding_validated`

## Grounded Teaching Package

A `GroundedTeachingPackage` includes:

* the original `PedagogicalContext`
* the primary Content Concept snapshot
* primary instructional evidence
* supporting evidence
* source references
* review status
* quality status
* grounding confidence
* metadata

## Evidence Model

Primary evidence is selected from the target Content Concept. It preserves:

* concept title
* concept description
* learning objective
* concept review status
* concept quality status
* source reference

Supporting evidence is collected deterministically from reachable parent context:

* parent Content Section
* source Learning Resource
* Curriculum when available
* Curriculum Unit when available
* Subject when available

## Source References

`SourceReference` captures:

* academic object type
* object id
* title
* relationship to the primary concept
* sequence number when applicable

Source references preserve provenance. They do not prove grounding quality by themselves; richer grounding validation remains future work.

## Service Boundary

`GroundingService` owns grounding-package construction and validation.

Service methods:

* `build_grounding_package(context)`
* `validate_grounding(package)`
* `list_source_references(package)`

The service is read-only. It consumes context snapshots and never mutates academic content.

## Validation

PI-4C validation checks that:

* the package contains a primary concept
* the package contains primary evidence
* the package preserves source references

Invalid packages return validation errors. Validation also publishes a business event with validity and error details.

## Events

The service publishes:

* `learning.grounding_package_created`
* `learning.grounding_validated`

## Architectural Boundaries

PI-4C does not include:

* prompt generation
* lesson generation
* LLM calls
* instructional strategies
* conversation behavior
* assessment
* learner progression

## Validation Commands

Human Docker validation should run:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py test apps.learning
```
