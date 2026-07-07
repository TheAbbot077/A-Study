# Phase 3C — Learning Resource Platform

## Purpose

The learning resource platform captures educational materials before ingestion or parsing. It focuses on representing resources that can later be processed or associated with curriculum structure.

## Architecture

- The capability lives in the academic app.
- Domain models remain in the domain layer and are surfaced through the Django bridge module.
- Service-layer operations are handled by LearningResourceService.
- Business events are published through the existing event platform.

## Core Model

LearningResource represents an instructional material record and can optionally reference a subject, curriculum, curriculum unit, institution, and stored file.

## Constraints

- Supported resource types: textbook, notes, guide, reference, other.
- Supported statuses: draft, active, archived.
- The model does not implement ingestion, parsing, upload APIs, or AI generation.
