# Phase 3D — Learning Content Platform

## Purpose

The learning content platform defines the canonical hierarchy for educational material content: sections and concepts. It stays focused on structural representation and does not introduce parsing, generation, or learner progress features.

## Architecture

- The capability lives in the academic app.
- Domain models live in the domain layer and are surfaced through the Django bridge module.
- Service-layer usage is handled by LearningContentService.
- Business events are published through the existing event platform.

## Core Models

- ContentSection: a sequence-based section within a LearningResource.
- ContentConcept: a sequence-based concept within a section.

## Constraints

- Section sequence numbers are unique per learning resource and must be at least 1.
- Concept sequence numbers are unique per content section and must be at least 1.
