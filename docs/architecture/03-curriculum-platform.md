# Phase 3B — Curriculum Platform

## Purpose

The curriculum platform introduces structured learning expectations under a Subject. It is intentionally scoped to defining curricula and their ordered units without introducing lessons, assessments, or learner progress.

## Architecture

- The curriculum capability lives in the academic app.
- Domain models live in the domain layer and are surfaced through the Django bridge modules.
- Service-layer orchestration is handled by CurriculumService.
- Business events are published through the existing event platform.

## Core Models

- Curriculum: associates a subject with an institution-scoped curriculum version.
- CurriculumUnit: defines an ordered unit within a curriculum.

## Constraints

- Curriculum uniqueness is enforced by subject, institution, and version.
- CurriculumUnit uniqueness is enforced by curriculum and sequence number.
- CurriculumUnit sequence numbers must be at least 1.

## Events

The curriculum platform publishes these business events:

- academic.curriculum_created
- academic.curriculum_updated
- academic.curriculum_archived
- academic.curriculum_unit_created
- academic.curriculum_unit_updated
- academic.curriculum_unit_archived
