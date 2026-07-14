# 03 - Domain Language

# Abbot Study Canonical Domain Language

## Purpose

This document defines the canonical vocabulary of Abbot Study.

Every engineer, architect, AI assistant, documentation author, and future contributor should use these terms consistently.

The objective is to prevent terminology drift as the platform grows.

---

# Core Principle

The Academic Domain is independent of:

* PDF files
* OCR
* AI models
* LLM prompts
* Import mechanisms
* Storage technology

Importers produce academic content.

The Academic Domain owns educational meaning.

---

# Platform Layer

## User

A person authenticated within the system.

Users may have one or more roles.

---

## Institution

A school, university, organization, or learning provider.

Institutions own configuration, users, and academic assets.

---

## Business Event

An immutable record describing something that has happened in the business domain.

Events describe facts, not commands.

Examples:

* subject_created
* assessment_completed
* mastery_awarded

---

## Stored File

A physical file managed by the Storage Platform.

Examples:

* PDF
* DOCX
* Image
* ZIP archive

Stored files are infrastructure assets.

They are **not** learning content.

---

# Academic Domain

## Subject

The highest-level academic container.

Examples:

* Mathematics
* Accounting
* Biology
* Constitutional Law

Everything educational belongs to a Subject.

---

## Curriculum

An approved academic structure for a Subject.

A Subject may have multiple Curriculum versions.

Only approved Curriculum becomes official.

---

## Curriculum Unit

A major subdivision within a Curriculum.

Examples:

* Algebra
* Financial Statements
* Cell Biology

Units organize learning expectations.

They are not physical textbook chapters.

---

## Learning Resource

Any educational material that supports learning.

Examples:

* Textbook
* Lecture notes
* Study guide
* Workbook
* Reference manual

A Learning Resource is a source of educational content.

---

## Content Section

The canonical structural subdivision of a Learning Resource.

Examples:

* Chapter
* Module
* Lesson
* Heading
* Unit within a guide

Different resource types may map differently.

The Academic Domain always refers to them as Content Sections.

---

## Content Concept

The smallest teachable academic idea.

Examples:

* Opportunity Cost
* Newton's Second Law
* Trial Balance
* Binary Search

Content Concepts are the primary learning units.

Teaching, assessment, and mastery all operate at this level.

---

# Import Domain

## Importer

A component that converts external material into the Academic Domain.

Examples:

* PDF importer
* DOCX importer
* EPUB importer
* Publisher API importer
* Manual importer

Importers never define educational rules.

---

## Resource Ingestion Job

A tracked process responsible for importing a Learning Resource.

Possible states include:

* Pending
* Processing
* Completed
* Failed
* Cancelled

---

## Parser

A specialised importer responsible for extracting structure from documents.

Parsers suggest academic structure.

They do not publish official curriculum.

---

# Learning Engine

## Teaching Session

A learner's active interaction with The Abbot for a single Content Concept.

Teaching Sessions include:

* Explanation
* Examples
* Questions
* Clarifications

Teaching Sessions do not determine progression.

---

## Pedagogical Session

The persisted canonical session record for a Teaching Session.

A Pedagogical Session belongs to one learner and one Content Concept.

It records lifecycle state but does not assess mastery or unlock progression.

---

## Pedagogical Message

An ordered message within a Pedagogical Session.

Messages may come from the learner, The Abbot, Ariel, or the system.

Pedagogical Messages preserve sequence and content for future teaching, review, and learning-continuity capabilities.

---

## Pedagogical Context

A stable context package assembled for a Pedagogical Session or a learner and Content Concept.

Pedagogical Context includes the learner, target concept, containing section, source learning resource, and reachable curriculum details.

Pedagogical Context is read-only. It does not generate lessons, prompts, assessments, or progression decisions.

---

## Grounded Teaching Package

A deterministic evidence package derived from Pedagogical Context.

Grounded Teaching Packages identify the primary Content Concept, supporting academic evidence, and source references.

They preserve provenance for future teaching orchestration but do not generate lessons or validate generated explanations.

---

## Source Reference

A pointer to an academic object used as instructional evidence.

Source References identify object type, object id, title, relationship, and sequence number when available.

---

## Instructional Strategy

A structured pedagogical approach selected for a Grounded Teaching Package.

Instructional Strategies define how the concept should be taught before conversation orchestration or AI language generation occurs.

---

## Strategy Step

One ordered instructional move within an Instructional Strategy.

Strategy Steps describe instructional goals and recommended interactions without producing learner-facing lesson text.

---

## Conversation Context

The structured dialogue state for a Pedagogical Session.

Conversation Context references the Grounded Teaching Package, Instructional Strategy, active conversation window, current turn number, and current instructional step.

---

## Conversation Turn

One ordered dialogue entry in a Pedagogical Session.

Conversation Turns preserve sender, interaction type, content, sequence, timestamp, and metadata.

---

## Conversation Window

The active chronological subset of Conversation Turns used for dialogue continuity.

Conversation Windows may support future summarization, but summarization is not part of the PI-4E implementation.

---

## Abbot Teaching Agent

The platform-owned orchestrator that prepares structured teaching responses from grounded evidence, instructional strategy, and conversation context.

The Abbot Teaching Agent does not define curriculum, award mastery, unlock progression, or call AI providers directly.

---

## Abbot Teaching Response

A structured response package produced by the Abbot Teaching Agent.

Abbot Teaching Responses contain sections, source references, strategy used, response type, and metadata.

---

## Learning Companion

A reusable non-primary teaching companion that supports learning presence, encouragement, reflection, or specialized practice without replacing The Abbot.

Learning Companions do not assess mastery, unlock progression, reorder curriculum, or override grounding.

---

## Ariel Companion

The first concrete Learning Companion.

Ariel supports reflection and session continuity, but PI-4G does not implement Ariel teach-back mastery.

---

## Companion Interaction

A structured companion request within a Pedagogical Session.

Companion Interactions identify the companion type, interaction type, session, and optional context.

---

## Companion Response

A deterministic companion output that may be recorded into the session conversation.

Companion Responses are supportive dialogue artifacts, not primary teaching content.

---

# Assessment Domain

## Assessment

A structured check of learner understanding for a Content Concept.

Assessments contain ordered Assessment Items and may have multiple learner attempts.

---

## Assessment Item

One prompt or task within an Assessment.

Assessment Items define the response format, but PI-5A does not generate questions or grade answers.

---

## Assessment Attempt

A learner's attempt at an Assessment.

Attempts track lifecycle state and contain submitted responses.

---

## Assessment Response

A learner-submitted response to an Assessment Item.

Assessment Responses preserve submitted data but do not imply correctness, mastery, or progression.

---

## Assessment Evaluation

A future evaluation record attached to an Assessment Response.

PI-5A defines the structure but does not implement grading.

---

## Assessment Result

A future result record derived from an Assessment Evaluation.

PI-5A defines the structure but does not award mastery or unlock content.

---

## Evidence of Learning Platform

The PI-5 platform layer that records learning evidence and produces explicit mastery decisions.

Assessment is one source of evidence; future sources may include teach-back, oral response, projects, simulations, and manual review.

---

## Learning Evidence

A historical record that a learner demonstrated, partially demonstrated, or failed to demonstrate understanding for a Content Concept.

Learning Evidence identifies the learner, Content Concept, source type, source id, evidence type, optional score, confidence, metadata, and creation time.

---

## Mastery Decision

A deterministic decision derived from Learning Evidence for one learner and one Content Concept.

Mastery Decisions are explicit records and may be `not_enough_evidence`, `not_mastered`, `emerging`, `mastered`, or `needs_review`.

---

## Mastery Profile

The current mastery state for one learner and one Content Concept.

A Mastery Profile summarizes the latest decision, confidence, evidence count, and most recent evidence timestamp. It does not unlock curriculum or perform learner progression.

---

## Assessment Strategy

A deterministic plan for what kind of assessment evidence should be collected for a Content Concept.

Assessment Strategies recommend item types, evidence requirements, ordered steps, and estimated difficulty. They do not create Assessment Items or grade learner responses.

---

## Assessment Blueprint

A planning artifact that combines a Content Concept with an Assessment Strategy.

Assessment Blueprints identify the concept, allowed item types, recommended item count, mastery signal, evidence requirements, and strategy steps.

---

## Assessment Evidence Requirement

A requirement describing what evidence type should be collected and the minimum confidence expected.

Evidence Requirements guide future assessment construction but do not by themselves award mastery or unlock progression.

---

## Item Bank

The reusable repository of authored assessment items for Content Concepts.

The Item Bank supports review, quality marking, options, and assessment linking. It does not generate questions or grade learner responses.

---

## Item Bank Entry

A reusable authored assessment item connected to a Content Concept.

Item Bank Entries include item type, prompt, explanation, difficulty, review status, quality status, optional author, metadata, and timestamps.

---

## Item Option

An ordered option belonging to an Item Bank Entry.

Item Options may record whether an option is correct, but PI-5D does not use that field to grade learner responses.

---

## Assessment Item Bank Link

An ordered link between an Assessment and an Item Bank Entry.

Assessment Item Bank Links allow assessments to reuse item bank entries while preserving assessment-specific ordering.

---

## Assessment Delivery Session

A learner's active delivery experience for an Assessment.

Assessment Delivery Sessions track status, linked attempt, current sequence number, timestamps, and metadata. They do not grade responses or update mastery.

---

## Assessment Delivery Item

The ordered item presented during an Assessment Delivery Session.

Assessment Delivery Items may wrap an Assessment Item or an Assessment Item Bank Link while preserving sequence order.

---

## Assessment Delivery State

The lifecycle state of an Assessment Delivery Session.

Supported states are `created`, `active`, `paused`, `submitted`, `completed`, and `abandoned`.

---

## Grading Platform

The assessment capability layer that evaluates submitted Assessment Responses and records explicit Evaluation and Result artifacts.

The Grading Platform does not award mastery, unlock progression, remediate learners, or generate questions.

---

## Assessment Evaluation

An explicit evaluation record for one Assessment Response.

Assessment Evaluations include score, max score, correctness, feedback, evaluator type, metadata, and timestamps.

---

## Assessment Result

An aggregate result record for an Assessment Attempt.

Assessment Results summarize total score, max score, percentage, optional pass/fail state, metadata, and timestamps.

---

## Deterministic Evaluator

A rule-based evaluator that grades supported response types using stored answer keys.

PI-5F supports deterministic grading for multiple choice and true/false responses when answer keys are available.

---

## Evidence Integration

The process of converting evaluated assessment artifacts into canonical Learning Evidence.

Evidence Integration preserves source provenance and does not update mastery, unlock progression, or trigger remediation.

---

## Evidence Provenance

The source identity and metadata that explain where a Learning Evidence record came from.

Evidence Provenance includes source type, source id, related assessment identifiers, scores, percentages, and evaluator details where available.

---

## Integrated Evidence

Learning Evidence created from an evaluated assessment artifact.

Integrated Evidence can be consumed by future mastery workflows but is not itself a Mastery Decision.

---

## Lesson Snapshot

A versioned, reviewable representation of a teaching session.

Snapshots support consistency, review, and reproducibility.

---

## The Abbot

The primary instructional intelligence.

Responsibilities:

* Teach
* Explain
* Clarify
* Encourage
* Adapt explanations

The Abbot never changes curriculum.

---

## Ariel

The learner's teach-back companion.

The learner teaches Ariel.

Ariel evaluates understanding through explanation rather than direct instruction.

---

# Assessment Domain

## Assessment

An evaluation of learner understanding for a single Content Concept.

Assessments may include:

* Multiple choice
* Short answer
* Essay
* Oral
* Calculation
* Case study
* Teach-back
* Project

---

## Assessment Attempt

A single learner submission for an Assessment.

Attempts are immutable historical records.

---

## Mastery

A determination that sufficient understanding has been demonstrated.

Mastery is recorded through approved business rules as an explicit Mastery Decision and current Mastery Profile.

---

## Sequential Unlock

The process that grants access to the next Content Concept after mastery.

No AI component may bypass Sequential Unlock rules.

---

## Remediation

Structured support provided after unsuccessful assessment.

Remediation never skips learning content.

---

## Remediation Platform

The evidence-oriented capability that transforms Learning Evidence into structured intervention plans.

The Remediation Platform is not assessment-specific. Assessment is one evidence producer among many.

---

## Remediation Plan

The overall remediation intervention for one learner and one Content Concept.

Remediation Plans move through explicit lifecycle states: pending, active, completed, escalated, cancelled, and closed.

---

## Remediation Recommendation

A recommended intervention generated from evidence patterns.

Recommendations may include lesson review, repeated activity, Ariel teach-back, additional questions, source material review, simulation, or educator review.

---

## Remediation Activity

Actual remediation work assigned within a plan.

Activities are future evidence producers and may include lesson replay, practice assessment, simulation, Ariel teach-back, programming task, or educator review.

---

## Remediation Outcome

The recorded result of remediation work.

Supported outcomes are improved, unchanged, regressed, and escalated.

---

## Assessment Review Platform

The quality assurance capability for assessments, reusable questions, and observed assessment performance.

The Assessment Review Platform is separate from assessment delivery, grading, evidence integration, and remediation.

---

## Assessment Review

The review record for an Assessment.

Assessment Reviews move through explicit review states: draft, pending_review, in_review, approved, needs_revision, rejected, and archived.

---

## Question Review

The review record for an Item Bank Entry.

Question Reviews support reusable item quality control outside any single assessment attempt.

---

## Quality Finding

A recorded issue, concern, or quality observation discovered during review.

Quality Findings may be linked to an Assessment Review or Question Review.

---

## Review Decision

An explicit outcome of a quality review.

Supported decisions include approved, needs_revision, rejected, and archived.

---

## Difficulty Calibration

A record comparing expected item difficulty with observed learner performance.

Difficulty Calibration preserves calibration direction, sample size, success rate, and rationale.

---

## Reviewer Assignment

A record that a reviewer has been assigned to an Assessment Review or Question Review.

Reviewer Assignments support workload tracking, reassignment, and completion history.

---

## Content Intelligence Platform

The ingestion capability that transforms raw learning-resource files into structured parsing artifacts and candidate academic content.

The Content Intelligence Platform is not the academic system of record.

---

## Content Import Job

The top-level import record for processing one learning resource file.

It tracks lifecycle, OCR decisions, confidence scores, and diagnostics.

---

## Content Processing Job

The orchestration aggregate that owns asynchronous processing state between a durable uploaded file and downstream parser stages.

Content Processing Jobs track stage, status, progress, active attempt, cancellation, and typed failure information.

---

## Processing Attempt

An immutable historical execution attempt for a Content Processing Job.

Retries create new Processing Attempts rather than rewriting old execution history.

---

## Processing Diagnostic

A stage-specific diagnostic record attached to both a Content Processing Job and a Processing Attempt.

Processing Diagnostics preserve safe public messages and structured operational details.

---

## Processing Stage Result

A durable completion envelope for one stage within one Processing Attempt.

Stage Results provide idempotency and stable output references for future processing capabilities.

---

## Parsed Document

The normalized parsed representation of an imported file.

---

## Parsed Section

A structured section candidate detected from a Parsed Document.

---

## Parsed Concept Candidate

A candidate concept extracted from a Parsed Section before academic publication.

---

## Content Extraction Result

The recorded extraction output including extraction method, text sufficiency, OCR usage, and structural metadata.

---

## Content Validation Finding

A structured issue discovered during import validation.

---

## Parser Pipeline Run

An execution record for a single content intelligence pipeline run.

---

# Student Intelligence

## Learner Profile

The canonical representation of a learner.

Includes:

* Preferences
* Pace
* Progress
* Historical performance

---

## Learner Digital Twin

The evolving educational model of an individual learner.

Represents predicted understanding rather than merely recorded history.

---

## Knowledge Graph

A graph representing relationships among Content Concepts.

Examples:

* Prerequisites
* Dependencies
* Similar concepts
* Duplicate concepts

The Knowledge Graph informs recommendations but does not replace official curriculum.

---

# AI Governance

## Grounding

The practice of ensuring AI responses are based on approved educational content whenever possible.

Grounding takes precedence over creativity.

---

## Hallucination

An AI-generated statement unsupported by approved evidence.

Hallucinations must be minimized, detected, and surfaced for review.

---

## Quality Review

A human and/or AI process that evaluates educational correctness, grounding, pedagogy, and safety.

Quality Review determines publication readiness.

---

# Administrative Domain

## Review

Human inspection of academic assets before publication.

---

## Approval

An explicit administrative action that promotes content into official use.

Approval cannot be performed automatically by AI.

---

## Publication

The act of making approved academic content available to learners.

Only published content may participate in official learning pathways.

---

# Engineering Vocabulary

## Program Increment (PI)

A major architectural milestone delivering a coherent platform layer.

Examples:

* PI-2 Platform Services
* PI-3 Academic Domain
* PI-4 Learning Engine

---

## Capability

A focused architectural unit within a Program Increment.

Examples:

* Subject Platform
* Curriculum Platform
* Learning Resource Platform

Every Capability follows the ASEM v2 lifecycle.

---

## Service

A business component responsible for implementing domain behaviour.

Business rules belong in Services.

---

## Domain Model

A business entity representing a concept within the domain.

Domain Models define meaning rather than framework behaviour.

---

## Business Event

An immutable statement describing something that has already happened.

Business Events communicate facts across the platform.

---

# Canonical Language Rules

Throughout Abbot Study:

* Say **Content Section**, not Chapter, unless referring specifically to a textbook.
* Say **Content Concept**, not Topic or Lesson.
* Say **Learning Resource**, not Document, unless referring specifically to a stored file.
* Say **Teaching Session**, not Chat.
* Say **Assessment Attempt**, not Quiz Result.
* Say **Mastery**, not Completion.
* Say **Sequential Unlock**, not Next Button.
* Say **Importer**, not Parser, unless specifically referring to parsing technology.
* Say **Learner Digital Twin**, not AI Profile.
* Say **Program Increment**, not Mega Phase.

When introducing new features, contributors should extend this document before introducing new terminology into the codebase.

A shared language is a core architectural asset. Consistent terminology is considered part of the system's design, not merely its documentation.
### Content extraction evidence

* **Source Document Profile** — immutable inspection evidence for one job attempt and source checksum.
* **Document Extraction** — versioned aggregate describing one completed extraction run.
* **Extracted Block** — ordered source evidence with an explicit origin; it is not an academic section or concept.
* **Evidence Origin** — whether a block was explicit in the source, inferred from layout/style/OCR, or supplied as a parser default.
* **Document Hierarchy** — one versioned reconstruction of structural relationships for an extraction result.
* **Hierarchy Node** — a source-ranged structural interpretation, not an Academic Platform section.
* **Block Classification** — an immutable interpretation of whether extraction evidence is body content, excluded noise, or review-required evidence.
* **Document Segmentation** — one versioned semantic grouping run over a document hierarchy.
* **Semantic Segment** — a meaningful, source-traceable content unit; it is neither a concept nor a retrieval chunk.
* **Academic Import Proposal** — a versioned recommendation for translating document understanding into Academic Platform content.
* **Proposed Section** — a reviewable section recommendation backed by a hierarchy node.
* **Proposed Concept** — a reviewable concept recommendation backed by meaningful semantic and extracted-block evidence.
* **Proposal Decision** — an auditable governance decision independent from publication.

## Retrieval Foundation

* **Retrieval Chunk** — the smallest searchable, versioned projection of approved Academic content with immutable provenance.
* **Retrieval Chunk Collection** — all chunks generated for one Academic Population version and chunk policy.
* **Retrieval Index Job** — a replay-safe record of chunking, embedding, indexing, diagnostics, and readiness.
* **Retrieval Readiness** — `not_indexed`, `indexing`, `indexed`, `stale`, or `failed`; only `indexed` can gate teaching readiness.
* **Grounding Package** — the exclusive durable evidence contract from Retrieval to Teaching.
* **Grounding Citation** — a reproducible reference from a ranked chunk through Academic, proposal, population, semantic segment, and source-page provenance.
* **Academic Population Job** — the idempotent publication aggregate that applies only approved proposal items.
