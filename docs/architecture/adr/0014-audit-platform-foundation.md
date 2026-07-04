# Audit Platform Foundation

## Status
Accepted

## Context

Abbot Study needs a shared capability for recording meaningful system actions across domains. The platform should support actor, institution, target, and metadata capture without introducing analytics or UI complexity in the first phase.

## Decision

We will introduce an Audit Platform in the backend with an AuditEntry model, an AuditService, and event publication for audit creation. The model will support basic querying by actor, institution, and target.

## Consequences

- Audit records become a reusable foundation for future compliance and observability workflows.
- The initial design remains scoped to recording and querying, without retention or analytics features.
