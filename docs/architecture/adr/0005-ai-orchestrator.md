# AI Orchestrator

## Status

Accepted

## Context

The system will eventually integrate multiple AI providers and model strategies. Direct dependency on a single provider would make experimentation and replacement difficult.

## Decision

The platform will use an AI orchestrator abstraction that routes requests through a provider interface. This keeps the application logic independent from specific AI vendors while allowing new providers to be introduced with minimal change.

## Consequences

Positive outcomes.

- Provider portability and easier experimentation.
- Cleaner separation between orchestration and implementation details.
- Better support for evaluation, safety, and prompt management.

Trade-offs.

- Additional abstraction may initially feel heavier than direct provider calls.
- Provider-specific behavior must be normalized through the shared interface.

Future implications.

- The orchestrator will become the entry point for AI-driven features across the platform.
- Future providers, routing rules, and evaluation strategies can be added incrementally.
