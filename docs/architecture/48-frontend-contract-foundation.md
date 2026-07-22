# Frontend Contract Foundation (PI-6E.1)

Status: implemented, awaiting manual Docker validation.

PI-6E.1 establishes typed frontend transport boundaries for the governed PI-6D pipeline without implementing the operational review, population, retrieval, or teaching-readiness screens.

## Backend-authoritative governance

The frontend displays backend lifecycle values and submits commands. It never infers approval, population, synchronization, or teaching readiness from progress, elapsed time, or another frontend state. A successful teaching-readiness response with decision `blocked` is valid governance data and is distinct from an HTTP/API failure.

## Contract organization

Feature-owned transport contracts and clients live under:

- `features/content-processing`
- `features/academic-population`
- `features/retrieval`
- `features/teaching-readiness`

The existing Academic Review service was tightened to use actual backend lifecycle unions and projection shapes. All clients reuse the cookie/CSRF-aware `apiRequest` boundary and forward optional abort signals.

## Failure, idempotency, and polling

`normalizeApiProblem` preserves HTTP status, backend code, safe message, field errors, structured blockers, and correlation ID. Network failures remain distinct from governed terminal failures.

`OperationIdempotency` scopes stable keys by resource and operation. Renders, double submissions, and uncertain retries reuse a key until the caller retires it after terminal completion.

`pollOperation` serializes requests, forwards cancellation, stops on caller-defined success or failure, supports transient-error policy, and prevents updates after the owning request is aborted. Workflow truth remains in backend terminal predicates.

## React validation recovery

Authentication, subject-list restoration, and subject-detail loading apply asynchronous results only while current. Subject changes invalidate stale requests. Subject-detail polling is abortable and non-overlapping. Nullable import jobs are structurally narrowed before actions. Assessment response state is keyed by question rather than copied synchronously in an effect.

No ESLint suppression, unsafe assertion, state library, dependency, route redesign, or complete operational PI-6E UI was introduced.

## Manual validation

```powershell
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
docker compose exec frontend npm run smoke:audit
docker compose exec frontend npm run smoke:e2e
```
