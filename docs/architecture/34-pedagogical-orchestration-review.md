# Pedagogical Orchestration Review

## Status

PI-4 hardening complete.

## Architecture Overview

The Pedagogical Orchestration Platform is the provider-agnostic learning layer between the Academic Domain and any future AI provider.

The platform owns:

* pedagogical sessions and messages
* context assembly
* grounding
* instructional strategy selection
* conversation orchestration
* Abbot teaching response orchestration
* reusable learning companions

It does not own assessment, mastery, progression, prompt generation, AI provider integration, or Ariel teach-back mastery.

## Canonical Teaching Pipeline

```text
Academic Domain
  -> Pedagogical Session
  -> Context Assembly Engine
  -> Grounding Engine
  -> Grounded Teaching Package
  -> Instructional Strategy Engine
  -> Conversation Orchestrator
  -> Abbot Teaching Agent
  -> Learning Companion Platform
  -> Future AI Provider boundary
```

The pipeline preserves the constitutional split:

* Academic Domain determines what is taught.
* Pedagogical services determine how teaching is prepared and orchestrated.
* Future AI providers may generate language only inside platform constraints.

## Completed Capabilities

* PI-4A - Pedagogical Session Platform
* PI-4B - Context Assembly Engine
* PI-4C - Grounding Engine
* PI-4D - Instructional Strategy Engine
* PI-4E - Conversation Orchestrator
* PI-4F - Abbot Teaching Agent
* PI-4G - Learning Companion Platform
* PI-4H - Pedagogical Orchestration Platform Hardening

## Dependency Graph

```text
PedagogicalSessionService
  <- ConversationOrchestratorService
  <- AbbotTeachingAgentService
  <- LearningCompanionService

ContextAssemblyService
  -> Academic Domain snapshots
  <- GroundingService
  <- ConversationOrchestratorService
  <- AbbotTeachingAgentService

GroundingService
  -> PedagogicalContext
  <- InstructionalStrategyService
  <- ConversationOrchestratorService
  <- AbbotTeachingAgentService

InstructionalStrategyService
  -> GroundedTeachingPackage
  <- ConversationOrchestratorService
  <- AbbotTeachingAgentService
```

Framework adapters remain thin. Domain value objects live in `apps.learning.domain.models`; `apps.learning.models` remains a Django discovery bridge.

## Hardening Findings

* Pedagogical mutations are service-owned.
* Event names are registered for discovery before subscribers exist.
* Message ordering remains canonical through `PedagogicalMessage.sequence_number`.
* Conversation and companion interactions now align with the expanded pedagogical message vocabulary.
* Abbot orchestration no longer keeps an unused direct `PedagogicalSessionService` dependency.
* No AI provider, prompt, assessment, mastery, or progression logic is present.

## Known Limitations

* Companion registry and activation state are in-process only.
* Abbot responses use deterministic placeholder generation.
* Grounding validation is structural, not semantic.
* Instructional strategy selection is rule-based and intentionally simple.
* Conversation summarization is not implemented.
* There is no public PI-4 API layer yet.

## Deferred Work To PI-5

* Assessment engine
* Question bank
* Mastery decisions
* Sequential unlocking enforcement
* Remediation
* Assessment history
* Bloom's Taxonomy integration

## Architectural Recommendations

* Keep PI-5 assessment services downstream of pedagogical sessions but independent of Abbot response generation.
* Introduce durable companion/session activation only when API or product flows require it.
* Keep future AI provider integration behind an explicit provider boundary.
* Add semantic grounding validation before allowing generated explanations to become learner-facing production content.
