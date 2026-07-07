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

Mastery is awarded through approved business rules.

---

## Sequential Unlock

The process that grants access to the next Content Concept after mastery.

No AI component may bypass Sequential Unlock rules.

---

## Remediation

Structured support provided after unsuccessful assessment.

Remediation never skips learning content.

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
