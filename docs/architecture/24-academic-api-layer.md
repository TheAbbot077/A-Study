# 24 - Academic API Layer

## Status

PI-3I implementation.

## Purpose

The Academic API Layer exposes controlled DRF endpoints for managing canonical academic domain objects.

The API layer is intentionally thin. It validates request and response shapes, enforces authenticated access, and delegates business mutations to academic services.

## Scope

PI-3I introduces API modules under the academic capability:

* apps/academic/api/serializers.py
* apps/academic/api/views.py
* apps/academic/api/urls.py

The root URL configuration registers academic routes under:

* /api/academic/

## Exposed Resources

The API exposes viewsets for:

* Subjects
* Curricula
* Curriculum Units
* Learning Resources
* Content Sections
* Content Concepts
* Resource Ingestion Jobs

## Mutation Boundary

Mutating endpoints delegate to existing services:

* AcademicStructureService
* CurriculumService
* LearningResourceService
* ManualAuthoringService
* ContentReviewService
* ResourceIngestionService

Serializers expose academic fields, but review metadata and ingestion lifecycle fields are changed through explicit service-backed actions rather than arbitrary writes.

## Supported Operations

Standard resources support:

* list
* retrieve
* create
* update
* partial_update
* archive where appropriate

Resource ingestion jobs support:

* list
* retrieve
* create
* start
* complete
* fail
* cancel

DELETE endpoints are not part of PI-3I.

## Review Actions

Content Section actions:

* submit-for-review
* approve
* reject
* mark-quality

Content Concept actions:

* submit-for-review
* approve
* reject
* mark-quality

These actions call ContentReviewService and do not publish learner-facing content.

## Permissions

PI-3I uses authenticated access as the minimum permission boundary.

Advanced role-based authorization is intentionally deferred until the platform has explicit academic administration permission primitives.

## Non-Goals

PI-3I does not implement:

* Frontend UI
* File upload APIs
* PDF parsing
* Parser execution
* Learner progress endpoints
* Assessment endpoints
* Advanced role-based authorization

## Architectural Boundary

The API layer coordinates HTTP concerns only.

Academic business rules remain in services. The API must not become the owner of curriculum, review, ingestion, or authoring behavior.
