# 02 - Program Roadmap

## Abbot Study Engineering Roadmap

### PI-0 - Product Constitution

**Status:** Complete

Defines the permanent educational and AI governance principles of the platform.

---

### PI-1 - Engineering Foundation

**Status:** Complete

Capabilities:

* Engineering conventions
* DDD architecture
* Docker foundation
* Backend foundation
* Frontend foundation
* ADR framework
* Framework integration

---

### PI-2 - Platform Services

**Status:** Complete

Capabilities:

* Identity Platform
* Event Platform
* Storage Platform
* Engineering Validation Toolkit
* Notification Platform
* Settings Platform
* Audit Platform

---

### PI-3 - Academic Domain

**Status:** Complete

Completed:

* Subject
* Curriculum
* Curriculum Unit
* Learning Resource
* Content Section
* Content Concept
* Resource Ingestion
* 3F - Importer Contracts
* 3G - Manual Authoring
* 3H - Quality & Review
* 3I - Academic APIs
* 3J - Academic Administration

Exit Criteria:

* Complete canonical academic domain
* Importer abstraction
* Manual authoring support
* Quality review workflow
* Public API
* Administrative tooling
* Documentation and ADRs complete

---

### PI-4 - Learning Engine

**Status:** In Progress

Focus:

* Teaching sessions
* Lesson orchestration
* Context assembly
* Grounded explanations
* Conversational tutoring
* Ariel session foundation

Completed:

* PI-4A - Pedagogical Session Platform

Remaining:

* Lesson orchestration
* Context assembly
* Grounded explanations
* Conversational tutoring
* Ariel session enrichment

---

### PI-5 - Assessment & Mastery

Focus:

* Assessment engine
* Question bank
* Mastery decisions
* Sequential unlocking
* Remediation
* Bloom's Taxonomy integration
* Assessment history

---

### PI-6 - Content Intelligence

Focus:

* Import pipelines
* PDF parsing
* OCR
* AI-assisted extraction
* Validation
* Canonicalization
* Import adapters
* Content quality scoring

---

### PI-7 - Student Intelligence

Focus:

* Forgetting curve
* Review scheduling
* Weakness detection
* Recommendations
* Learning analytics

---

### PI-8 - Learner Digital Twin

Focus:

* Learner profile
* Confidence
* Pace
* Retention
* Misconceptions
* Personalized interventions

---

### PI-9 - Knowledge Intelligence

Focus:

* Knowledge graph
* Concept dependencies
* Difficulty modelling
* Learning pathways
* Graph inspection

---

### PI-10 - Multi-Agent Intelligence

Focus:

* Teacher Agent
* Professor Agent
* Simplifier Agent
* Socratic Agent
* Coach Agent
* Visual Teacher Agent
* Shared grounding
* Output validation

---

### PI-11 - Autonomous Content Factory

Focus:

* Lesson generation
* Flashcards
* Assessments
* Mnemonics
* Diagrams
* Case studies
* Remediation plans
* Cached learning assets

---

### PI-12 - AI Governance

Focus:

* Grounding review
* Hallucination detection
* Pedagogical review
* Curriculum review
* Safety review
* Human approval workflows

---

### PI-13 - Optimization

Focus:

* Model routing
* Token tracking
* Cost optimisation
* Cache utilisation
* Batch generation
* Institutional cost controls

---

# Program Increment 4 — Pedagogical Engine

**Status:** Planned

## Mission

Transform approved academic knowledge into structured pedagogical experiences while remaining independent of any specific AI provider.

The Pedagogical Engine determines *how* learning occurs.

The Academic Domain determines *what* is taught.

AI providers generate language within the constraints established by the Pedagogical Engine.

---

## Guiding Principles

* Pedagogy is independent of conversation.
* Conversation is independent of AI providers.
* AI assists instruction but does not determine educational policy.
* Every teaching interaction is grounded in approved academic content.
* Teaching strategy is selected before language generation.
* The Learning Engine remains provider-agnostic.

---

## PI-4 Capabilities

### 4A — Pedagogical Session Platform

Canonical models:

* PedagogicalSession
* PedagogicalMessage
* PedagogicalState

Provides the lifecycle for every pedagogical interaction.

---

### 4B — Context Assembly Engine

Builds the complete instructional context from:

* Subject
* Curriculum
* Learning Resource
* Content Section
* Content Concept
* Historical session context
* Supporting references

Produces a canonical teaching context for downstream components.

---

### 4C — Grounding Engine

Ensures every instructional response is grounded in approved academic content.

Tracks:

* source references
* supporting evidence
* curriculum alignment
* content provenance

---

### 4D — Instructional Strategy Engine

Selects the pedagogical approach appropriate for the concept.

Example strategies include:

* Direct Instruction
* Worked Example
* Guided Practice
* Socratic Dialogue
* Analogy
* Visual Explanation
* Concept Mapping
* Problem-Based Learning

The strategy engine determines *how* a concept should be taught before any AI generation occurs.

---

### 4E — Conversation Orchestrator

Manages:

* conversation history
* clarification flow
* follow-up questions
* context pruning
* response sequencing

This component manages dialogue rather than pedagogy.

---

### 4F — Abbot Teaching Agent

Coordinates:

* Pedagogical Session
* Context Assembly
* Grounding
* Instructional Strategy
* Conversation Orchestrator

Produces structured teaching responses while remaining independent of a specific AI provider.

---

### 4G — Ariel Learning Companion Foundation

Introduces Ariel into pedagogical sessions.

Provides:

* shared session awareness
* memory hooks
* future teach-back readiness

Teach-back remains part of a later Program Increment.

---

### 4H — Pedagogical Engine Hardening

Program Increment review covering:

* architecture
* documentation
* ADRs
* event coverage
* regression tests
* Docker validation
* readiness for PI-5

---

## Exit Criteria

PI-4 is complete when the platform can orchestrate a complete pedagogical session from approved academic content without embedding educational policy inside an AI provider or conversation layer.


### PI-15 - Prep Season

Focus:

* Interview simulation
* Thesis defence
* Admissions interviews
* Professional examinations
* Multi-examiner orchestration

---

### PI-16 - Productization

Focus:

* Progressive Web App
* Mobile applications
* Offline learning
* Production monitoring
* Security
* Compliance
* Public beta
* Institutional rollout

---

## Engineering Principle

Every Program Increment delivers a coherent architectural layer. Every capability within a Program Increment follows the ASEM v2 lifecycle:

1. Program Increment Charter
2. Capability Contract
3. Design Checkpoint
4. Scoped Master Prompt
5. AI-Assisted Implementation
6. Docker Validation
7. Architecture Review
8. Capability Commit
9. Program Increment Review

No capability is considered complete until it has passed validation, architecture review, and documentation requirements.
