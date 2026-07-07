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

## Decision 004: Academic Domain Before Learning Engine

The Academic Domain must be hardened as the canonical content layer before PI-4 Learning Engine begins.

Reason:

Teaching, grounded explanations, and future learner progression must consume stable academic structures rather than redefine curriculum, content, review, or importer boundaries.

## Decision 005: Pedagogical Session Platform Before Orchestration

PI-4 begins with a canonical Pedagogical Session and ordered Pedagogical Message model before AI orchestration, prompts, lesson generation, assessment, or progression.

Reason:

Future teaching capabilities need a deterministic session substrate and event contract before they can safely add adaptive behavior.
