# 25 - Academic Admin Integration

## Status

PI-3J implementation.

## Purpose

Academic Admin Integration gives platform operators a safe Django admin surface for inspecting and managing academic domain records.

Django admin is an operational adapter. It is not the domain layer and must not own academic business rules.

## Scope

PI-3J registers Django admin classes for:

* Subject
* Curriculum
* CurriculumUnit
* LearningResource
* ContentSection
* ContentConcept
* ResourceIngestionJob

Admin classes provide:

* list_display fields for operational scanning
* list_filter fields for common academic and review dimensions
* search_fields for text lookup
* readonly_fields for identifiers, audit timestamps, and lifecycle timestamps
* service-backed save hooks for add and change forms where direct edits are allowed
* safe bulk actions that delegate to services
* direct deletes disabled in favor of explicit archive and lifecycle services

## Admin Actions

Safe admin actions include:

* archive selected subjects
* archive selected curricula
* archive selected curriculum units
* archive selected learning resources
* archive selected content sections
* archive selected content concepts
* submit selected sections for review
* approve selected sections
* reject selected sections
* submit selected concepts for review
* approve selected concepts
* reject selected concepts

## Service Delegation

Admin add/change hooks and admin actions delegate to existing services:

* AcademicStructureService
* CurriculumService
* LearningResourceService
* ManualAuthoringService
* ContentReviewService

The admin layer does not implement archive, approval, rejection, authoring, deletion, or review state rules directly. ResourceIngestionJob records are inspectable in admin, while lifecycle mutation remains service/API-owned.

## Non-Goals

PI-3J does not implement:

* custom frontend UI
* custom admin dashboards
* custom templates
* parser controls
* upload flows
* learner progress admin
* advanced permissions
* learner-facing operations

## Architectural Boundary

Django admin is for trusted operational management.

It may invoke service-layer operations, but it must not become the owner of curriculum, authoring, review, ingestion, or learning behavior.
