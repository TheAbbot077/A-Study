# Notification Platform Foundation

## Status
Accepted

## Context

Abbot Study needs a reusable notification capability that is independent of email, learning, documents, or AI concerns. The foundation should support pluggable channels and simple lifecycle events without introducing a production delivery backend yet.

## Decision

We will introduce a Notification Platform in the backend with a Notification model, channel abstraction, and NotificationService. The initial implementation will use a logging channel provider and publish lifecycle events for created and sent notifications.

## Consequences

- Notifications can be created and processed without coupling to one delivery provider.
- The platform remains intentionally simple and does not yet support real delivery integrations.
- Future work can add additional channels and operational delivery backends.
