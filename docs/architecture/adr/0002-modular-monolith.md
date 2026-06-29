# Modular Monolith

## Status

Accepted

## Context

The system is expected to grow across teaching, assessment, analytics, and AI workflows. A fully distributed architecture would introduce operational overhead too early for the current scope.

## Decision

The platform will start as a modular monolith. Domain capabilities will be organized into separate Django apps with explicit boundaries, while shared infrastructure remains centralized within the backend application.

## Consequences

Positive outcomes.

- Simpler deployment and operations.
- Clear internal modules without premature distributed complexity.
- Easier refactoring as the product evolves.

Trade-offs.

- Module boundaries must be maintained carefully to avoid coupling.
- Scaling concerns may require decomposition later.

Future implications.

- The monolith can evolve into service decomposition when domain boundaries justify it.
- Teams can work within a single application while preserving modularity.
