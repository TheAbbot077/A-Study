# Backend Operational Runbook

This runbook covers the operator-facing recovery and readiness path for the PI-9.4 and PI-9.5 backend hardening slices.

## First response

Start with safe signals:

1. `python manage.py report_backend_operational_readiness`
2. `python manage.py report_backend_release_gate`
3. domain integrity or release-readiness commands for the affected bounded context

Do not start with ad hoc database editing.

## Operational readiness signals

The backend readiness report surfaces:

- database availability posture;
- durable event backlog counts;
- retryable event deliveries;
- terminal event failures;
- stuck processing deliveries.

The backend release gate surfaces:

- the combined readiness posture from existing domain services;
- configuration blockers;
- release warnings;
- a safe summary for operator review.

## Recovery matrix

### PostgreSQL unavailable

- Status: `UNAVAILABLE`
- Operator action: restore database access before resuming writes.
- Do not attempt learner-facing writes against partial state.

### Redis unavailable

- Status: `DEGRADED` or `UNAVAILABLE` depending on deployment role.
- Operator action: confirm whether the deployment uses Redis only for async coordination or also for synchronous product paths.
- If Redis is async-only, preserve durable state and allow safe degraded operation where supported.

### Celery workers unavailable

- Status: `DEGRADED`
- Operator action: inspect durable event backlog and task queue state.
- Safe behavior: keep durable state intact and allow retryable work to resume when workers return.

### Event backlog increasing

- Status: `DEGRADED`
- Operator action: inspect pending, retryable, terminal, and stuck delivery counts.
- Safe behavior: do not declare the backend unavailable unless synchronous traffic is actually unsafe.

### Terminal event failures present

- Status: `NOT_READY`
- Operator action: inspect the durable event ledger and delivery failure codes.
- Safe behavior: preserve the failure record and repair the root cause before replaying anything.

### Content processing stuck

- Status: `DEGRADED`
- Operator action: use the existing content-processing operational and reconciliation paths.
- Safe behavior: do not invent successful completion.

### Storage provider unavailable

- Status: `DEGRADED` or `UNAVAILABLE`
- Operator action: verify whether the affected workflow can queue for recovery or must fail closed.
- Safe behavior: do not claim file persistence succeeded if the backing store did not persist.

### Assessment evaluation failures

- Status: `DEGRADED` or `NOT_READY` depending on the failure scope
- Operator action: inspect the evaluation and evidence integration surfaces.
- Safe behavior: do not mutate mastery or evidence manually.

### Recovery failures

- Status: `NOT_READY`
- Operator action: inspect the recovery/reassessment contract and its deterministic blockers.
- Safe behavior: preserve lineage and retry only through governed recovery services.

## Database and backup posture

- PostgreSQL is the authoritative durable store for academic truth, identity, events, assessments, mastery history, journeys, and audit metadata.
- File/object storage must be backed up together with its metadata.
- Redis is not authoritative for academic truth; if present, treat it as broker/cache/ephemeral coordination unless a bounded deployment-specific contract says otherwise.

## Restore order

1. Stop writes or isolate the environment.
2. Restore PostgreSQL.
3. Restore file/object storage to a compatible point.
4. Verify configuration and secrets.
5. Verify migrations.
6. Bring up core dependencies.
7. Run the backend readiness and integrity commands.
8. Inspect durable event backlog state.
9. Inspect domain release-readiness reports.
10. Reconcile rebuildable projections only.
11. Resume traffic once the gate is ready.

## Forbidden actions

- Do not rewrite academic truth from backups.
- Do not invent mastery, evidence, assessment outcomes, or remediation success.
- Do not treat a healthy response path as proof that all durable state is healthy.

