# Decision Log

## Decision 001: Foundation Before AI

We will build deterministic architecture before introducing AI-heavy features.

Reason:

The product depends on strict learning order, source grounding, admin review, and mastery-based unlocking. These must exist before advanced AI features are added.

## Decision 002: Codex Later

Codex will not be used during the earliest foundation phase.

Reason:

Codex is useful for implementation and acceleration, but only after the architecture and rules are stable enough to constrain its output.

## Decision 003: Modular Monolith First

The first version will use a modular monolith backend rather than microservices.

Reason:

This keeps the system easier to build, test, deploy, and reason about while still allowing future service extraction if scale demands it.