# Django Domain Model Bridge

## Status

Accepted

## Context

Django requires models to be discoverable through app-level model modules, while Abbot Study prefers to keep real domain implementations in a domain-oriented location. Without a bridge, the project would either violate Django conventions or blur framework integration with domain design.

## Decision

Abbot Study keeps real model implementations in apps/<app>/domain/models.py and uses apps/<app>/models.py as a thin Django discovery bridge. The bridge imports and re-exports the domain model so Django can discover it without relocating the implementation.

## Consequences

Positive outcomes.

- Django model discovery works as expected.
- Domain models remain organized under a domain-focused structure.
- Framework integration stays thin and maintainable.

Trade-offs.

- The bridge introduces a small amount of indirection.
- Contributors must understand the convention to avoid confusion.

Future implications.

- The same pattern can guide other thin framework adapters as the system grows.
