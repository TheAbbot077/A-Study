# ADR: Phase 3C Learning Resource Platform

## Status
Accepted

## Context
The platform needs a lightweight way to represent educational materials before any ingestion or parsing workflow is introduced.

## Decision
We will add a LearningResource domain model under the academic app with lifecycle and optional references to subject, curriculum, curriculum unit, institution, and stored file. The implementation will stay scoped to representation and basic lifecycle management without introducing upload APIs, parsing, or AI-generated content.

## Consequences
- The platform can track and organize learning materials in a structured manner.
- Future ingestion and parsing workflows can build on this foundation without mixing concerns.
- The scope remains intentionally narrow for Phase 3C.
