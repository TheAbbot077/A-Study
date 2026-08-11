# Backend Release Gate Recovery Matrix

This matrix summarizes the primary backend readiness and recovery signals used by PI-9.5 operator guidance.

| Condition | Operational status | Primary signal | Recovery posture |
|---|---|---|---|
| PostgreSQL unavailable | UNAVAILABLE | readiness command / database errors | restore database first |
| Redis unavailable | DEGRADED or UNAVAILABLE | readiness command / deployment context | restore or allow async-only degradation |
| Celery workers unavailable | DEGRADED | backlog growth / worker absence | recover workers, preserve durable state |
| Durable event backlog increasing | DEGRADED | pending/retryable counts | drain backlog, do not drop records |
| Terminal event failures present | NOT_READY | terminal failure count | fix root cause before replay |
| Learning journey readiness NOT_READY | NOT_READY | learning-journey readiness report | resolve blockers in that bounded context |
| Learning experience readiness NOT_READY | NOT_READY | learning-experience readiness report | resolve blockers in that bounded context |
| Debug mode enabled in production | NOT_READY | configuration check | disable debug mode |
| SECRET_KEY unsafe or default | NOT_READY | configuration check | rotate to a production-safe secret |
| Missing required app registration | NOT_READY | app installation check | repair deployment wiring |

## Supported recovery principles

- Use governed services and commands first.
- Preserve lineage and durability.
- Reconcile projections only when they are explicitly rebuildable.
- Keep recovery bounded and deterministic.

## Command set

- `python manage.py report_backend_operational_readiness`
- `python manage.py report_backend_release_gate`
- context-specific integrity and release-readiness commands

## Reporting rule

The release gate must fail closed when a blocker implies a credible present risk to:

- security;
- tenant isolation;
- privacy;
- academic truth;
- data integrity;
- idempotency;
- concurrency;
- async reliability;
- migration correctness;
- operational recovery.

