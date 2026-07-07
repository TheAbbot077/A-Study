# 26 - Academic Domain Architecture Review

## Status

PI-3K architecture hardening review.

## Purpose

This document records the PI-3K review of the Academic Domain before PI-4 Learning Engine begins.

The review confirms that the Academic Domain is a production-quality architectural layer for canonical academic content, review, authoring, ingestion tracking, APIs, and admin operations. It does not introduce Teaching Sessions, assessments, AI behavior, parser improvements, or learner progression.

## Architecture Overview

The Academic Domain owns educational meaning:

* Subject
* Curriculum
* Curriculum Unit
* Learning Resource
* Content Section
* Content Concept
* Resource Ingestion Job

The domain is implemented as a Django app with framework-aware persistence models in `apps.academic.domain.models`. `apps.academic.models` remains a discovery bridge that re-exports the domain models for Django.

Business mutations are owned by services:

* AcademicStructureService
* CurriculumService
* LearningResourceService
* LearningContentService
* ManualAuthoringService
* ContentReviewService
* ResourceIngestionService

Adapters coordinate external access:

* DRF API viewsets validate HTTP requests and delegate mutations to services.
* Django admin provides operational inspection and service-backed admin actions/forms.
* Importer contracts produce proposed academic content structures without persistence.

## Dependency Graph

```text
Academic API -> Academic Services -> Academic Domain Models
Academic Admin -> Academic Services -> Academic Domain Models
Academic Importers -> Import DTOs -> Academic Services, when persisted by callers
Academic Services -> Business Events -> Event Platform
Academic Domain Models -> Users, Storage platform models

Academic Domain Models do not call APIs, admin classes, importers, AI providers, or learning-engine code.
```

## Capability Summary

| Capability | Status | Architecture Document | ADR | Tests |
| --- | --- | --- | --- | --- |
| Subject | Complete | 02-domain-model.md | 0008-django-domain-model-bridge.md | test_subjects.py |
| Curriculum | Complete | 03-curriculum-platform.md | 0003-service-layer.md | test_curriculum.py |
| Curriculum Unit | Complete | 03-curriculum-platform.md | 0003-service-layer.md | test_curriculum.py |
| Learning Resource | Complete | 04-learning-resource-platform.md | 0003-service-layer.md | test_learning_resources.py |
| Content Section | Complete | 05-learning-content-platform.md | 0003-service-layer.md | test_learning_content.py |
| Content Concept | Complete | 05-learning-content-platform.md | 0003-service-layer.md | test_learning_content.py |
| Resource Ingestion Job | Complete | 05-ai-architecture.md | 0004-event-driven-architecture.md | test_resource_ingestion.py |
| Importer Contracts | Complete | 21-importer-contracts.md | 0015-importer-contracts.md | test_importer_contracts.py |
| Manual Authoring | Complete | 22-manual-authoring-platform.md | 0016-manual-authoring-platform.md | test_manual_authoring.py |
| Content Quality & Review | Complete | 23-content-quality-review-platform.md | 0017-content-quality-review-platform.md | test_content_review.py |
| Academic API Layer | Complete | 24-academic-api-layer.md | 0018-academic-api-layer.md | test_academic_api.py |
| Academic Admin Integration | Complete | 25-academic-admin-integration.md | 0019-academic-admin-integration.md | test_academic_admin.py |
| Academic Domain Hardening | Complete pending Docker validation | 26-academic-domain-review.md | 0020-academic-domain-hardening.md | test_academic_architecture.py |

## Review Findings

### Domain Model Consistency

The Academic Domain uses canonical terminology from `03-domain-language.md`: Subject, Curriculum, Curriculum Unit, Learning Resource, Content Section, Content Concept, Importer, Resource Ingestion Job, Review, Approval, and Quality Review.

StoredFile remains a storage platform asset and is not treated as learning content.

### Service Boundaries

Business mutations are service-owned. PI-3K hardened Django admin form saves so direct admin add/change writes delegate to services, and direct admin deletes are disabled in favor of explicit archive/lifecycle operations. Resource Ingestion Job records remain inspectable in admin while lifecycle mutation stays with ResourceIngestionService and API/service workflows.

### Dependency Direction

The dependency direction remains adapter -> service -> domain model. Services publish events through the Event Platform. No Academic Domain code depends on Learning Engine, Assessment, AI providers, frontend code, or parser implementations.

### Event Coverage

Academic business events are registered in the EventRegistry for discoverability. Service methods publish events for creation, update, archive, review, authoring reorder, resource activation/archive, and ingestion lifecycle transitions.

### API Consistency

The Academic API layer is thin and service-backed. DELETE endpoints are not exposed. Review and ingestion lifecycle transitions use explicit actions.

### Admin Consistency

The admin layer is an operational adapter. Bulk actions and mutable form saves delegate to services, and direct deletes are disabled. Ingestion jobs are protected from direct admin lifecycle mutation.

### Migration Review

Academic migrations are ordered by capability:

1. Subject
2. Curriculum and CurriculumUnit
3. LearningResource
4. ContentSection and ContentConcept
5. ResourceIngestionJob
6. Content review fields

No accidental migration noise or obsolete migration files were identified during this pass.

### Test Review

Existing coverage includes services, APIs, admin, importer contracts, manual authoring, review workflow, and ingestion lifecycle behavior. PI-3K adds architecture regression coverage for academic event registration and admin service-boundary behavior.

## Completed Capabilities

PI-3 now contains the canonical Academic Domain layer required before PI-4:

* Academic structure
* Curriculum structure
* Learning resources
* Canonical content sections and concepts
* Resource ingestion tracking
* Importer contract boundary
* Manual authoring
* Content quality and review workflow
* Academic API layer
* Academic admin integration
* Architecture hardening review

## Known Limitations

* Advanced role-based academic permissions are deferred.
* Resource ingestion tracks lifecycle but does not execute parser pipelines.
* Importers define contracts and manual structured transformation only.
* Admin remains operational and minimal, not a custom academic workflow product.
* Review and approval establish content readiness, but learner publication/progression behavior belongs to future increments.

## Deferred Work To PI-4

PI-4 may consume approved Content Concepts through Teaching Sessions and lesson orchestration. PI-4 must not redefine Academic Domain ownership, bypass review workflows, or reorder canonical content.

The following remain outside PI-3K:

* Teaching Sessions
* Lesson Snapshots
* Context assembly
* Grounded explanations
* Conversational tutoring
* Ariel session foundation

## Deferred Work Beyond PI-4

The following are intentionally not introduced in PI-3K:

* Assessments and mastery decisions
* Sequential Unlock implementation
* Parser improvements
* OCR and AI extraction
* Frontend workflows
* Knowledge graph intelligence

## Architectural Recommendations

* Keep future Learning Engine services read-oriented against approved academic content until explicit publication and progression rules exist.
* Introduce role-based academic permissions before exposing admin-grade API operations broadly.
* Keep parser and AI extraction work behind importer contracts so external content mechanisms do not leak into the Academic Domain.
* Prefer new business events over cross-domain imports when PI-4 needs to react to academic changes.
