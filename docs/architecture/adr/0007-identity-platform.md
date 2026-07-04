# Identity Platform

## Status

Accepted

## Context

Abbot Study needs a dependable platform capability for account ownership, institutional membership, roles, and identity-related events. Treating identity as a narrow login/logout concern would leave the system without a clear foundation for multi-tenant access, audits, and future authentication integrations.

## Decision

Abbot Study treats Identity as a platform capability rather than a simple authentication feature. The users app will own identity-facing concerns such as accounts, profiles, memberships, roles, and related events, while keeping other domains focused on their own responsibilities.

## Consequences

Positive outcomes.

- Clear ownership of user and account concerns.
- Better support for institutions and future identity integrations.
- A stronger foundation for audits, roles, and event-driven workflows.

Trade-offs.

- Identity services must remain disciplined to avoid absorbing unrelated domain logic.
- The initial model may be broader than a minimal auth implementation.

Future implications.

- The identity platform can evolve into a robust foundation for SSO, onboarding, and enterprise-grade access control.
