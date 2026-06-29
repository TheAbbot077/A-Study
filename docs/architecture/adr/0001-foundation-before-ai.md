# Foundation Before AI

## Status

Accepted

## Context

The platform needs a stable technical foundation before introducing AI capabilities. Without a clear domain structure, shared abstractions, and reliable service boundaries, AI features would be layered onto unstable code.

## Decision

The project will first establish a disciplined Django-based foundation with clear app boundaries, shared core abstractions, and a consistent service-oriented structure. AI features will be introduced only after the base architecture supports extension without unnecessary coupling.

## Consequences

Positive outcomes.

- Faster onboarding for contributors.
- Clear separation between domain and infrastructure concerns.
- Easier future integration of AI features.

Trade-offs.

- Initial delivery focuses on foundation rather than novel capabilities.
- Some early work may feel generic compared with shipping user-facing AI features.

Future implications.

- The foundation will support incremental expansion into analytics, assessments, and intelligent workflows.
- Future AI work can reuse the established patterns rather than creating parallel structures.
