# Event Platform Foundation

## Status
Accepted

## Context

Abbot Study needs a lightweight way for domains to publish business events without introducing database persistence, Celery, or a large infrastructure footprint. The first version should support synchronous in-process dispatch so teams can build event-driven patterns incrementally.

## Decision

We will implement an in-process event platform inside the core package with a public EventPublisher, an EventDispatcher, an EventRegistry, and simple callable subscribers. Domains may publish events, but the platform will be responsible for delivery mechanics while subscribers remain responsible for their own reactions.

## Consequences

- Domains can publish business events without coupling to infrastructure details.
- Subscriber failures will be logged and will not crash the publishing flow.
- The initial design is intentionally simple and does not yet include durable persistence or asynchronous delivery.
- Future iterations can evolve this foundation toward Celery-backed or database-backed event processing.
