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

## Decision 012: Content Processing Orchestration Before Parser Expansion

PI-6C introduces a dedicated Content Processing bounded context before further parser-quality, retrieval, or AI-assisted extraction work.

Reason:

Uploaded-file processing needs authoritative orchestration state, immutable attempts, typed failures, retry policy, and cancellation semantics before later parsing and indexing capabilities can scale safely.
## PI-6C.2 layout-aware extraction decisions

* Inspection and extraction remain separate PI-6C.1 stages.
* File formats are detected using signatures and container structure, not extensions alone.
* Ordered, versioned layout blocks are durable source evidence, not academic sections.
* Native text is preferred; mixed PDFs receive selective OCR.
* Header/footer candidates, tables, images, coordinates, and style evidence are preserved when available.
* DOCX body ordering includes interleaved paragraphs and tables.
* Legacy flat text is a compatibility projection; PI-6C.3 owns hierarchy reconstruction.

## PI-6C.3 hierarchy and segmentation decisions

* Hierarchy is reconstructed evidence, not academic truth.
* Structuring and segmentation remain separate PI-6C.1 stages.
* Document-wide evidence precedes local heading heuristics.
* Front matter, back matter, navigation, and noise remain durable classifications.
* A table of contents supports but never dictates body hierarchy.
* Weak documents receive explicit conservative fallback groups.
* Every hierarchy node and semantic segment remains traceable to extracted blocks.
* Semantic segments are neither concepts nor retrieval chunks.
* Legacy sections are temporary projections of hierarchy and segmentation outputs.

## PI-6C.4 proposal and population decisions

* Parser and semantic-segment outputs never create Academic Platform truth directly.
* Academic interpretation is persisted as a reviewable, evidence-backed proposal.
* Proposal approval and Academic Platform population are separate state machines.
* Existing automatic imports use a durable compatibility approval decision.
* Every proposed concept requires semantic-segment and extracted-block provenance.
* Population is versioned, replay-safe, and mapped back to proposed items.
* Only approved proposals in `ready_for_population` may publish.
* Retrieval, indexing, tutor grounding, and teaching readiness remain deferred to PI-6C.5.
## PI-6C.5 retrieval decisions

Retrieval is a projection rather than a source of truth; `GroundingPackage` is its exclusive Teaching contract; embedding and index providers are isolated behind ports; hybrid vector/keyword/metadata retrieval is the default; and indexing readiness is gated by completed, approved Academic Population.

## PI-6C.6 semantic governance decisions

* `READY_FOR_REVIEW` is not approval. The legacy field remains `processing` for compatibility, while all lifecycle consumers prioritize the authoritative processing status and treat review as a governed pause.
* `READY_FOR_REVIEW` is terminal for automatic processing but not for the full publication lifecycle.
* Automatic acceptance is an explicit versioned policy evaluation with durable evidence.
* Heading evidence cannot satisfy concept evidence; substantive body blocks are required.
* TOC regions own their navigation entries and cannot independently create academic content.
* Blocking proposal findings prevent automatic acceptance and population.
* Quantity and page-ratio guardrails are independent of confidence.
* Population requires an approval decision newer than the latest validation snapshot.
# Decision: Population consumes approved projections

PI-6D.1 establishes that machine proposals are immutable and never directly edited or selectively populated. Human governance produces an immutable approved projection; that projection is the sole population input. Automatic policy acceptance also materializes an all-items projection to preserve this invariant.

# Decision: Approval and population are separate capabilities

PI-6D.2 makes readiness evaluation and projection creation durable, versioned, checksummed, and idempotent. Approval transitions the proposal and projection to `READY_FOR_POPULATION` but performs no population dispatch. PI-6D.3 exclusively owns Academic Platform writes and downstream retrieval/teaching transitions.
