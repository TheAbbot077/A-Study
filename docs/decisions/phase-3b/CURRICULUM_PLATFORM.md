# ADR: Phase 3B Curriculum Platform

## Status
Accepted

## Context
The platform needs a scoped curriculum capability that defines structured learning expectations under a Subject without expanding into lessons, assessments, or learner progress.

## Decision
We will add a curriculum capability to the existing academic app with two domain models:

- Curriculum
- CurriculumUnit

The implementation will follow the repository architecture pattern with domain models in the domain layer, Django bridge modules in the app-level models.py file, a service layer, and business event publication through the existing event platform.

## Consequences
- The platform can define curriculum structure in a consistent, architecture-first way.
- The scope remains limited to curriculum definition and ordering.
- Future learning experiences can build on this foundation without conflating it with assessment or progress features.
