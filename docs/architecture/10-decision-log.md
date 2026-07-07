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

## Decision 006: Context Assembly Before Teaching Generation

The Learning Engine will assemble a stable Pedagogical Context before introducing prompt generation, lesson generation, grounding validation, assessment, or progression.

Reason:

Future teaching behavior needs a deterministic, source-aware context package that preserves academic authority without mutating academic content.

## Decision 007: Grounding Before Prompting

The Learning Engine will create a deterministic Grounded Teaching Package before prompts, lessons, conversation, assessment, or progression.

Reason:

Source-grounded teaching requires explicit instructional evidence and provenance before any generated teaching behavior is introduced.

## Decision 008: Strategy Before Conversation

The Learning Engine will select an Instructional Strategy before conversation orchestration or AI language generation.

Reason:

Pedagogical approach is educational policy and must remain deterministic, auditable, and platform-owned before downstream language generation begins.

## Decision 009: Conversation Before Agent Language

The Learning Engine will manage structured Conversation Context before introducing teaching agents or AI language generation.

Reason:

Dialogue state, turn ordering, and active window management are platform responsibilities and must remain independent of prompt generation and AI providers.

## Decision 010: Abbot Orchestration Before AI Providers

The Abbot Teaching Agent will coordinate teaching pipeline outputs and produce deterministic structured responses before any AI provider integration.

Reason:

Teaching orchestration must remain platform-owned, source-grounded, and testable before dynamic prompt generation or provider-specific language generation is introduced.

## Decision 011: Companion Platform Before Ariel Specialization

Learning companions will be implemented as a reusable platform, with Ariel as the first concrete deterministic companion.

Reason:

Companion behavior should support learning without replacing The Abbot or hard-coding Ariel-specific assumptions into the teaching pipeline.
