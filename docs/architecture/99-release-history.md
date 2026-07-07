# Release History

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
