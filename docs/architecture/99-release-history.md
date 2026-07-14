# Release History

## v0.6.0 - Content Intelligence MVP

PI-6A introduced the first production-ready Content Intelligence Platform slice.

Completed capabilities:

* content import job lifecycle
* PDF and DOCX extraction adapters
* OCR fallback recording
* parsed document, section, and concept candidate artifacts
* deterministic confidence scoring
* structured validation findings
* academic population through Academic services
* content intelligence API, admin, tests, and events

Major architectural decisions:

* Content Intelligence is a separate capability in `apps.content_intelligence`.
* Imported files are treated as raw evidence rather than academic truth.
* Academic remains the system of record for resources, sections, and concepts.
* OCR is fallback-only in PI-6A.

Validation remains pending human Docker execution.

## v0.5.2 - Assessment Platform Hardening

PI-5J completed the production-readiness hardening pass for the Evidence of Learning Platform.

Completed capabilities:

* lifecycle and validation hardening across PI-5 services
* domain-oriented exception standardization
* review and remediation API failure-path hardening
* assessment delivery and evaluation guardrails
* admin consistency improvements
* final PI-5 architecture consolidation

Major architectural decisions:

* PI-5 remains behaviorally stable while becoming operationally safer.
* Shared domain exceptions clarify business failures without breaking existing `ValueError` expectations.
* API adapters translate predictable domain failures into client errors rather than server errors.
* PI-5 documentation now represents the canonical completed Evidence of Learning Platform.

Validation remains pending human Docker execution.

## v0.5.1 - Assessment Review Platform

PI-5I introduced the Assessment Review Platform.

Completed capabilities:

* Assessment review lifecycle management
* Question review workflow
* Quality findings and review decisions
* Reviewer assignment and workload tracking
* Deterministic difficulty calibration
* Assessment review analytics
* Review event integration

Major architectural decisions:

* Quality assurance is isolated in `apps.assessment_review`.
* Review workflow is explicit and separate from delivery, grading, evidence integration, and remediation.
* Difficulty calibration is rule-based and replaceable.
* Review automation hooks consume existing platform events without introducing a parallel event system.

Validation remains pending human Docker execution.

## v0.5.0 - Assessment Foundation

PI-5A introduced the canonical Assessment Foundation.

Completed capabilities:

* Assessment domain models
* Assessment item model and item type vocabulary
* Assessment attempt lifecycle foundation
* Assessment response capture
* Evaluation and result placeholders for future grading/mastery
* AssessmentService
* Assessment business events

Major architectural decisions:

* Assessment is a separate bounded capability in `apps.assessments`.
* PI-5A captures assessment structure and attempts without grading or mastery.
* Future mastery and progression services must consume assessment records rather than redefine them.

Validation remains pending human Docker execution.

## v0.4.0 - Pedagogical Orchestration Platform

PI-4 completed the provider-agnostic pedagogical orchestration layer.

Completed capabilities:

* Pedagogical Session Platform
* Context Assembly Engine
* Grounding Engine
* Instructional Strategy Engine
* Conversation Orchestrator
* Abbot Teaching Agent
* Learning Companion Platform
* Pedagogical Orchestration Platform Hardening

Major architectural decisions:

* Teaching sessions are canonical learning interaction records.
* Context assembly is read-only and consumes the Academic Domain.
* Grounding packages preserve source evidence and provenance before strategy or response generation.
* Instructional strategies are selected deterministically before conversation or language generation.
* Conversation orchestration owns dialogue state but does not determine pedagogy.
* The Abbot Teaching Agent orchestrates structured responses without AI provider integration.
* Learning companions are reusable; Ariel is the first deterministic companion.
* Assessment, mastery, learner progression, and AI provider integration remain outside PI-4.

Readiness for PI-5:

* PI-4 provides the session, context, grounding, strategy, conversation, Abbot, and companion foundation needed by Assessment & Mastery.
* Human Docker validation remains required before tagging or release acceptance.
