# Academic API Layer

## Status
Accepted

## Context

Abbot Study has accumulated the core academic capabilities needed to manage canonical academic content: subjects, curricula, curriculum units, learning resources, content sections, content concepts, resource ingestion, importer contracts, manual authoring, and content review.

The platform now needs a controlled HTTP surface for trusted academic management workflows. ASEM v2 requires APIs to remain thin and delegate business behavior to services.

## Decision

We will introduce an Academic API Layer under apps/academic/api.

The API will expose DRF viewsets for:

* Subject
* Curriculum
* CurriculumUnit
* LearningResource
* ContentSection
* ContentConcept
* ResourceIngestionJob

Routes will be registered under /api/academic/.

Mutations will delegate to existing services:

* AcademicStructureService
* CurriculumService
* LearningResourceService
* ManualAuthoringService
* ContentReviewService
* ResourceIngestionService

Review and ingestion lifecycle transitions will use explicit custom actions instead of arbitrary field writes.

The minimum permission boundary is authenticated access. Advanced role-based authorization is deferred.

## Consequences

* Academic domain management has a consistent HTTP surface.
* API code remains thin and service-backed.
* Review and ingestion workflows are exposed without moving business logic into viewsets.
* File upload, parser execution, learner progress, assessment endpoints, frontend UI, and advanced authorization remain outside PI-3I.
