# Approved Academic Retrieval Synchronization (PI-6D.4)

Status: implemented, pending manual Docker/pytest validation.

PI-6D.4 adds a controlled handoff from a successful `AcademicPopulationRun` to the Retrieval Platform. It ends at `SYNCHRONIZED`; it neither evaluates nor sets `READY_FOR_TEACHING`. Frontend consumption remains deferred.

## Authority and boundaries

`academic_review` supplies immutable projection and population lineage. An infrastructure query adapter reconciles population mappings with active, approved `ContentSection` and `ContentConcept` records. Official Academic descriptions are the only indexed substantive text. Content-processing semantic-segment and page evidence supplies citations but cannot override accepted Academic titles, placement, order, or content.

Application services consume immutable gateway snapshots. Cross-context ORM access is confined to the retrieval infrastructure adapter.

## Readiness and manifest

The read-only readiness service verifies populated lifecycles, matching projection/source fingerprints, complete section and concept mappings, active approved Academic ownership, source locators, and provider availability. It reports stable blocker codes and performs no mutation or provider work.

The manifest builder deterministically orders mapped Academic concepts and creates stable chunk keys from resource, section/concept population keys, Academic content fingerprint, ordinal, chunk policy, and schema version. Manifest identity also includes citation, embedding, and hybrid-index versions. Every chunk requires a semantic-segment reference, truthful page range, and source fingerprint. Active citation coverage must be 100%.

## Candidate generations and promotion

A synchronization run creates a `BUILDING` candidate generation. Embeddings and candidate chunks are built outside the promotion transaction. Promotion locks the run and current active generation, rechecks the source fingerprint, reconciles counts and citations, promotes the candidate, and only then supersedes the prior active generation. A database constraint permits one active generation per resource. Failure marks only the candidate and attempt failed; the prior active generation remains active.

Legacy PI-6C.5 chunks and index jobs remain readable. `RetrievalChunk` was evolved with optional generation membership and nullable legacy collection/population fields so the new PI-6D.3 lineage does not require a parallel chunk concept.

## Idempotency, failure, and events

Request idempotency keys are unique and bound to a material request fingerprint. Matching replay returns the original run; changed input conflicts. Equivalent active or in-progress manifest work is reused without provider calls. Failed attempts are immutable history and retry uses a new key/run.

Started, failed, promoted, superseded, and completed events contain identifiers and counts only and are published after transaction commit. Completion never implies teaching readiness.

## Backend contracts

- `GET /api/academic-review/population-runs/{id}/retrieval-readiness/`
- `POST /api/academic-review/population-runs/{id}/synchronize-retrieval/`
- `GET /api/retrieval/synchronization-runs/{id}/`

The POST requires `expected_source_fingerprint`, `idempotency_key`, and optionally `reason`. The current deterministic local provider makes synchronization synchronous; a new run returns 201 and replay returns 200.

## Manual validation

Run only after reviewing the migration:

```powershell
docker compose exec backend python manage.py migrate
docker compose exec backend pytest apps/retrieval/tests/test_approved_academic_synchronization.py
docker compose exec backend pytest apps/retrieval/tests apps/academic_review/tests
```
