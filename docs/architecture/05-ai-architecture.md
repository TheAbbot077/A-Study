# 05 AI Architecture

## PI-6C.1: Content Processing Orchestration

Before parser quality, retrieval, or AI-assisted extraction are expanded, the platform now places a deterministic Content Processing orchestration layer between uploaded files and parser execution.

Responsibilities:

* asynchronous stage dispatch
* typed processing failures
* retry and cancellation policy
* immutable attempt history
* durable stage-result tracking
* safe polling state for the frontend

The legacy parser remains temporarily wrapped behind a compatibility stage adapter. AI-assisted extraction remains deferred.

## Phase 3E: Resource Ingestion Platform

The academic app now includes a lightweight ingestion lifecycle for learning resources. Resource ingestion jobs track the status of a resource transformation pipeline without implementing parsing or asynchronous execution yet.

### Responsibilities
- Track ingestion jobs for a learning resource and optionally an uploaded file.
- Record the source of the ingestion request and the user who requested it.
- Publish lifecycle events for creation, start, completion, failure, and cancellation.

### Supported events
- academic.resource_ingestion_job_created
- academic.resource_ingestion_job_started
- academic.resource_ingestion_job_completed
- academic.resource_ingestion_job_failed
- academic.resource_ingestion_job_cancelled
## Document evidence boundary

PI-6C.2 extraction is deterministic document processing, not academic interpretation. Native PDF text is preferred to OCR, mixed documents use page-selective OCR, and all inferred layout/style classifications remain evidence for later hierarchy reconstruction.

PI-6C.3 uses deterministic document-wide and lexical policies before any optional semantic provider. Provider output, if introduced later, remains evidence only. Hierarchy nodes and semantic segments cannot create concepts, retrieval indexes, or teaching readiness.

PI-6C.4 makes proposal generation an evidence-producing interpretation step. Even high-confidence deterministic or future provider output must pass proposal validation and a recorded review decision before population. Publication remains a separate deterministic service.

PI-6C.5 adds provider-independent embedding and retrieval ports. Retrieval implementations, including the optional PostgreSQL/pgvector adapter, remain infrastructure concerns. AI and Teaching consumers receive only a durable `GroundingPackage` with ranked evidence and complete citations; they never receive vectors, provider clients, or index APIs.
