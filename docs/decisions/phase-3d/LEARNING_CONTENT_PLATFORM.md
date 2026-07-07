# ADR: Phase 3D Learning Content Platform

## Status
Accepted

## Context
The platform needs a canonical content hierarchy for resources that can be used as the basis for future parsing, ingestion, and presentation workflows.

## Decision
We will add ContentSection and ContentConcept to the academic app, using the existing domain/service/event architecture. The implementation will remain limited to structural representation and ordering for Phase 3D.

## Consequences
- The platform can represent content hierarchy consistently.
- Future workflows can build on this structure without conflating it with assessment or learner progress concerns.
