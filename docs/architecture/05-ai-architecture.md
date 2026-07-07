# 05 AI Architecture

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
