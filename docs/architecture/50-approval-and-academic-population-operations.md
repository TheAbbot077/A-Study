# Approval and Academic Population Operations (PI-6E.3)

Status: implemented, awaiting manual Docker validation.

## Route and scope

The protected governance workspace is:

`/dashboard/academic-review/:proposalId/governance`

Completed reviews link to this route. It preserves navigation to the read-only review and source resource. The workflow is deliberately staged:

The review-to-governance link carries the authoritative review-session ID as query context. This lets the governance page use session retrieval after approval closes proposal-start semantics, without inventing a proposal-to-session lookup endpoint.

1. backend approval-readiness snapshot;
2. approval or rejection command;
3. immutable approved projection;
4. backend population readiness;
5. controlled Academic population;
6. populated result.

`APPROVED` does not mean `POPULATED`. `POPULATED` does not mean `SYNCHRONIZED`. `POPULATED` does not mean `READY_FOR_TEACHING`.

## Authoritative contracts

The workspace uses the registered PI-6D.2 and PI-6D.3 endpoints under `academic-review/sessions/`, `academic-review/projections/`, and `academic-review/population-runs/`.

Approval readiness receives the expected session version. Approval receives the readiness snapshot ID, expected session version, and stable operation idempotency key. Rejection receives a nonblank reason, expected session version, and a separately scoped stable key.

The approved projection is loaded from the backend and remains read-only. It is never assembled from mutable review items. Population readiness is requested only after a projection exists. Population receives only the projection checksum and stable idempotency key; the frontend never submits Academic section or concept content.

Population completes synchronously in PI-6D.3. The returned run/result is rendered directly, so no simulated progress or unnecessary polling is used. Existing run detail is loaded when readiness supplies a run ID.

There is no approval-decision retrieval endpoint and no explicit population retry endpoint. The frontend does not invent either. Failed population runs remain inspectable; a new deliberate attempt can use the existing population contract only where backend readiness permits it and must receive a new operation key.

## Failure and uncertain outcomes

Normalized API problems preserve status, code, safe message, field errors, blockers, and correlation ID. Stable keys remain allocated when a command has an uncertain network outcome or fails before an authoritative result, enabling same-command replay. Keys retire only after confirmed terminal success.

Stale version, lifecycle, integrity, population conflict, and validation failures remain visible in the governance workspace. No command retries automatically against newer state.

## Accessibility

The workflow uses semantic stage headings, native modal confirmations, labeled rejection input, keyboard-accessible projection navigation, textual lifecycle states, focus-visible controls, responsive stacked layouts, overflow-safe identifiers, and a live population-result region.

## Explicit exclusions

PI-6E.3 does not edit reviews or projections, mutate Academic records directly, synchronize retrieval, inspect retrieval generations, evaluate teaching readiness, or publish learner content.

## Manual validation

```powershell
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
docker compose exec frontend npm run smoke:audit:test
docker compose exec frontend npm run smoke:audit
docker compose exec frontend npm run smoke:e2e
```
