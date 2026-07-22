# Upload processing authority

## Authority and identity

A resource upload creates three durable identities:

1. the stored-file identifier returned by `POST /api/storage/files/`;
2. the Academic learning-resource identifier returned by `POST /api/academic/learning-resources/`;
3. the legacy Content Intelligence import identifier returned by `POST /api/content-intelligence/import-jobs/`.

For PI-6C and later uploads, the import response also exposes `processing_job_id`. This is the identifier of the canonical `ContentProcessingJob`. The canonical job owns lifecycle, stage, progress, active attempt, diagnostics, failure, retry eligibility, and cancellation eligibility. Its endpoint is:

```text
GET /api/content-processing/jobs/{processing_job_id}/
```

The processing attempt has its own identifier and is available through:

```text
GET /api/content-processing/jobs/{processing_job_id}/attempts/
```

The backend relation is `ContentProcessingJob.legacy_import_job`, a one-to-one compatibility and lineage link to `ContentImportJob`. The identifiers on either side of this relation are not interchangeable.

Canonical-only historical or administrative resources can resolve their latest institution-scoped job through:

```text
GET /api/content-processing/jobs/?resource={resource_id}
```

**Legacy import progress is not authoritative when a canonical ContentProcessingJob exists.**

## Upload handoff and polling ownership

After creating the legacy import record, the frontend reads its `processing_job_id`, resolves the canonical job once, and permanently switches that mounted workflow to canonical polling. It does not continue polling the legacy detail endpoint after linkage.

One non-overlapping polling loop owns each active resource in a mounted workflow. Canonical terminal states stop polling. Route changes and unmount abort the active request and timer. Historical records without `processing_job_id` retain legacy polling and actions.

The shared interval for multi-minute processing is five seconds. Transient transport and server errors remain polling concerns; they do not convert an active job into a failed job. Only an authoritative backend failure state is displayed as failed.

## Presentation and governance

Resource cards show the canonical stage label, progress, attempt number, last confirmed update, safe diagnostics, and both lineage identifiers. Long extraction is displayed as active regardless of elapsed time. Parser warnings are shown only when the canonical diagnostics API provides a learner-safe public message.

Canonical processing completion does not grant review approval, population, retrieval synchronization, or teaching readiness. The governed-workflow timeline consumes the canonical processing status while every downstream stage remains backend-authoritative.

Canonical retry and cancel commands use `/api/content-processing/jobs/{processing_job_id}/retry/` and `/cancel/`. Legacy-only retry continues to use the legacy import identifier. Legacy deletion remains responsible for deleting the upload lineage according to the existing deletion contract.

## Manual diagnostics

Inspect worker transitions without exposing document payloads:

```powershell
docker compose logs --since=30m celery
docker compose logs --tail=200 backend
```

In the browser network panel, confirm that a linked upload performs repeated requests only to:

```text
/api/content-processing/jobs/{processing_job_id}/
```

The legacy import detail endpoint must not remain an active polling source after canonical linkage.
