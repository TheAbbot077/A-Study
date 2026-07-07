# Academic Admin Integration

## Status
Accepted

## Context

Abbot Study needs a minimal operational admin surface for academic records. The academic domain now includes subjects, curricula, curriculum units, learning resources, content sections, content concepts, resource ingestion, manual authoring, review workflows, and APIs.

ASEM v2 requires business logic to remain in services. Django admin should support operational workflows without becoming the domain layer.

## Decision

We will add Django admin integration for the academic capability.

The admin integration will register:

* Subject
* Curriculum
* CurriculumUnit
* LearningResource
* ContentSection
* ContentConcept
* ResourceIngestionJob

Admin classes will include useful list displays, filters, search fields, and readonly fields.

Admin add/change forms for mutable academic records will delegate persistence to services so Django admin does not bypass business events. Direct deletes are disabled in favor of explicit archive and lifecycle operations. ResourceIngestionJob admin remains inspectable, but direct add/change mutation is restricted because ingestion lifecycle transitions belong to ResourceIngestionService and explicit API/service workflows.

Safe bulk actions will delegate to services:

* AcademicStructureService for subject archive
* CurriculumService for curriculum and unit archive
* LearningResourceService for learning resource archive
* ManualAuthoringService for content section and concept archive
* ContentReviewService for section and concept review actions

## Consequences

* Platform operators can inspect and manage academic records safely through Django admin.
* Archive and review actions remain service-backed and event-publishing.
* Admin form edits for mutable academic records remain service-backed and event-publishing.
* Direct academic deletes are not available through Django admin.
* Resource ingestion jobs remain protected from direct admin lifecycle edits.
* Admin integration does not introduce parser controls, upload workflows, learner progress operations, custom dashboards, or advanced permissions.
* Django admin remains an adapter over the academic domain rather than the owner of business behavior.
