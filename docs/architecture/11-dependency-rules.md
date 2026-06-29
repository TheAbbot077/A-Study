# Dependency Rules

## Purpose

This document defines the guiding dependency rules for the Abbot Study architecture. The goal is to keep the system modular, testable, and resilient as new features are introduced.

## Core Rules

1. Views may call Services.
2. Services may call Domain Models.
3. Services may publish Business Events.
4. Business Events may trigger asynchronous work.
5. Views must never directly call AI providers.
6. Only the AI Orchestrator may communicate with AI Providers.
7. AI Providers never access the database directly.
8. Repositories (when introduced) own ORM persistence.
9. Cross-domain communication should prefer Business Events over direct imports.
10. Circular dependencies between domains are prohibited.

## Dependency Diagram

```text
View -> Service -> Domain Model
   \-> Business Event -> Async Worker

View -> AI Orchestrator -> AI Provider
AI Provider -> External API

Repository -> ORM / Database
```

## Guidance

- Keep request handling thin in views.
- Put orchestration and application workflows in services.
- Use events for loose coupling across domains.
- Keep AI integration behind the orchestrator boundary.
- Reserve repositories for persistence concerns so domain code does not depend directly on ORM details.
