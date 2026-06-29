# Service Layer

## Status

Accepted

## Context

Business logic should not be embedded directly into the presentation or persistence layers. This would make the system harder to test and harder to evolve as requirements change.

## Decision

The project will use a service layer to hold application orchestration and domain operations. Repositories, infrastructure adapters, and domain models will be kept separate from service-level workflows.

## Consequences

Positive outcomes.

- Cleaner separation of responsibilities.
- Easier unit testing and reuse of workflows.
- Better support for future integrations and background processing.

Trade-offs.

- Additional abstraction can increase initial implementation effort.
- Services must remain focused to avoid becoming utility containers.

Future implications.

- The service layer will become the main integration point for use cases and cross-cutting workflows.
- New features can be added with less impact on controllers or persistence code.
