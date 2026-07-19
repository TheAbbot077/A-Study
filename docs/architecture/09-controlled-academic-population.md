# PI-6D.3 — Controlled Academic Population

Status: implemented; awaiting manual Docker validation.

PI-6D.3 is the single controlled handoff from an immutable approved proposal projection to official Academic Platform content. Academic Review authorizes and projects; Academic Population coordinates; the Academic bounded context creates `ContentSection` and `ContentConcept` truth through a typed application facade.

## Lifecycle and integrity

An `AcademicPopulationRun` moves `PLANNED → POPULATING → POPULATED`; `FAILED` is immutable attempt history. The approved projection moves `READY_FOR_POPULATION → POPULATING → POPULATED`. A failed transaction leaves the projection ready for a new-key retry. Population never sets `READY_FOR_TEACHING`.

Each run stores an immutable structured plan containing projection fingerprint, target identifiers, deterministic source keys, source order, provenance, totals, and the `provenance_only_no_fuzzy_matching` policy. Every populated section and concept has a durable mapping to its approved projection item.

## Idempotency, collision, and retry

The same idempotency key with equivalent material input returns the completed run. Reuse with different input is rejected. A database constraint permits at most one populated run per projection. Matching is permitted only by durable population provenance; title, normalized title, subject, resource, or position alone never establish identity. An occupied Academic sequence therefore causes a structured conflict and the atomic transaction rolls back.

A retry uses a new key and the unchanged projection fingerprint. Failed attempts are not edited. Changed content must return through review and create a new approved projection.

## Transaction and events

Authorization, blank input, stale fingerprint, obvious replay, and duplicate-success checks occur before the transaction. Inside one transaction the projection claim is locked, rechecked, materialized, mapped, reconciled, and completed. Completion events are registered with `transaction.on_commit`.

Events: `academic_population.planned`, `academic_population.started`, `academic_population.completed`, `academic_population.failed`, and `approved_proposal.populated`. Payloads contain identifiers, actor, lifecycle, and counts rather than academic content.

## Exclusions

This capability does not generate or edit proposals, rebuild approved projections, index retrieval content, create embeddings, declare teaching readiness, fuzzy-merge, overwrite, delete, or roll back Academic truth.

## Manual validation

Run from the repository root:

```powershell
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py test apps.academic_review
docker compose exec backend python manage.py test apps.academic
docker compose exec backend python manage.py check
docker compose exec frontend npm test -- --runInBand
```
