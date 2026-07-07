# 06 – Teaching Pipeline

# Abbot Study Canonical Teaching Pipeline

## Purpose

This document defines the canonical teaching pipeline used by every instructional interaction within Abbot Study.

The pipeline separates educational reasoning from conversation management and AI language generation.

This architecture ensures that educational policy remains under the control of the platform rather than the AI provider.

---

# Design Philosophy

Teaching is not prompt engineering.

Teaching is the orchestration of multiple architectural components, each with a clearly defined responsibility.

Every stage in the pipeline receives structured input and produces structured output for the next stage.

---

# Canonical Pipeline

```text
Academic Domain
        │
        ▼
Pedagogical Session
        │
        ▼
Context Assembly Engine
        │
        ▼
Grounding Engine
        │
        ▼
Grounded Teaching Package
        │
        ▼
Instructional Strategy Engine
        │
        ▼
Conversation Orchestrator
        │
        ▼
Abbot Teaching Agent
        │
        ▼
Learning Companion Platform
        │
        ▼
AI Provider
        │
        ▼
Learner
```

---

# Stage Responsibilities

## Academic Domain

Owns the canonical educational structure.

Provides:

* Subject
* Curriculum
* Curriculum Unit
* Learning Resource
* Content Section
* Content Concept

Determines **what** is taught.

---

## Pedagogical Session

Represents a learner's instructional interaction.

Owns:

* session lifecycle
* instructional messages
* session state

Provides continuity for teaching.

---

## Context Assembly Engine

Collects the academic information required for a teaching interaction.

Produces:

* PedagogicalContext

The Context Assembly Engine selects relevant information.

It does not determine instructional authority.

---

## Grounding Engine

Transforms a PedagogicalContext into a GroundedTeachingPackage.

Responsibilities include:

* authoritative evidence selection
* provenance
* source references
* quality indicators
* grounding validation

Determines what instructional evidence is permitted.

---

## Grounded Teaching Package

The canonical instructional payload.

Contains:

* pedagogical context
* primary evidence
* supporting evidence
* source references
* quality metadata

Every downstream teaching component consumes this object.

---

## Instructional Strategy Engine

Determines the most appropriate pedagogical approach.

Possible strategies include:

* Direct Instruction
* Worked Example
* Guided Practice
* Socratic Dialogue
* Visual Explanation
* Analogy
* Concept Mapping
* Problem-Based Learning

Determines **how** a concept should be taught.

Implemented in PI-4D as a deterministic rule-based service that consumes Grounded Teaching Packages and produces Instructional Strategies.

---

## Conversation Orchestrator

Manages dialogue.

Responsibilities:

* conversational flow
* clarification
* follow-up
* response sequencing
* conversation history

Does not determine pedagogy.

Implemented in PI-4E as a deterministic service that manages Conversation Context, Conversation Turns, and active Conversation Windows without generating language.

---

## Abbot Teaching Agent

Coordinates the complete teaching process.

Consumes:

* Grounded Teaching Package
* Instructional Strategy
* Conversation Context

Produces structured teaching responses.

The Abbot orchestrates instruction but does not define educational policy.

Implemented in PI-4F as a provider-agnostic orchestration service with deterministic placeholder response generation.

---

## Learning Companion Platform

Supports non-primary teaching companions.

Companions may provide:

* presence
* encouragement
* reflection prompts
* session summaries
* specialized practice support in future capabilities

Companions do not determine curriculum, grounding, instructional strategy, assessment, mastery, or progression.

Implemented in PI-4G as a reusable companion platform with Ariel as the first deterministic companion.

---

## AI Provider

Generates natural language.

Examples may include hosted or local language models.

The provider receives structured instructions and returns language.

It does not determine:

* curriculum
* learning order
* instructional strategy
* grounding
* mastery

---

# Architectural Principles

The pipeline is intentionally layered.

Each layer has a single responsibility.

No downstream layer should recreate work already completed upstream.

The AI provider is the final implementation component rather than the architectural centre of the system.

---

# Future Evolution

Future Program Increments will extend this pipeline with:

* Assessment Engine
* Ariel Teach-Back
* Knowledge Graph
* Learner Digital Twin
* Multi-Agent Teaching
* AI Quality Council

These capabilities will extend the pipeline while preserving its architectural direction.

---

# Living Document

This document is part of the constitutional architecture of Abbot Study.

As Program Increments are completed, this document shall be updated to reflect implemented capabilities while preserving the canonical teaching pipeline and its architectural intent.
