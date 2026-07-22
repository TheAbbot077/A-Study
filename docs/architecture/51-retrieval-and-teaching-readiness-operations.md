# PI-6E.4 Retrieval and Teaching-Readiness Operations

Status: implemented; awaiting manual validation.

PI-6E.4 extends the existing protected Academic governance workspace with two
backend-authoritative stages:

1. Retrieval synchronization after a successful Academic population run.
2. Teaching-readiness evaluation after a successful synchronization run.

The governing distinctions are:

- POPULATED does not mean SYNCHRONIZED.
- SYNCHRONIZED does not mean READY_FOR_TEACHING.
- READY_FOR_TEACHING does not necessarily mean learner-published.

## Retrieval synchronization

The workspace reads synchronization readiness from the population-run endpoint
and displays its source fingerprint, expected scope, active-generation identity,
blockers, and warnings. An enabled command requires backend readiness and sends
only the expected source fingerprint, a stable operation idempotency key, and an
optional reason.

The command response is authoritative. Although PI-6D.4 currently completes the
command synchronously, the UI safely polls the registered run-detail endpoint
when a planned or synchronizing response is returned. Polling is serial and
stops at synchronized or failed. Retry reuses the synchronization command,
because PI-6D.4 exposes no separate retry route, and receives a new scoped
idempotency key.

Generation data is read-only. PI-6D.4 exposes the generation identifier and
index/citation metrics on readiness and synchronization-run responses; it does
not expose a generation-detail or manual-promotion API. No such route or action
is invented by the frontend. A failed replacement therefore continues to show
the backend-reported active generation from readiness.

## Teaching readiness

The resource status endpoint controls presentation of not evaluated, blocked,
ready for teaching, and stale states. Evaluation and reevaluation use the same
registered command with distinct stable idempotency scopes. The request contains
the backend-provided lineage fingerprint when available and never contains a
requested outcome or frontend-calculated checks.

BLOCKED is rendered as a valid evaluation result. Checks retain their backend
category, pass state, severity, expected and observed values, explanation, and
related identifiers. Filters affect display only and never authoritative totals.
STALE removes current-ready emphasis and retains the latest historical
evaluation and invalidation reason.

## Accessibility and responsive behavior

Commands use named modal dialogs, native focus management, labelled optional
reason fields, textual lifecycle states, a live synchronization region, a
labelled readiness summary, keyboard-operable filters, semantic disclosures,
and text descriptions in addition to color. Metric grids stack on small screens
and identifiers wrap.

## Explicit exclusions

This stage does not edit chunks or checks, inspect embeddings, promote or delete
generations, override blockers, publish to learners, or invoke tutor behavior.

## Manual validation

From the repository root:

```powershell
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
docker compose exec frontend npm run smoke:audit
docker compose exec frontend npm run smoke:audit:test
docker compose exec frontend npm run smoke:e2e
```
