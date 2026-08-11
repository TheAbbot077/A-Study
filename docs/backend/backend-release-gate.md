# Backend Release Gate

PI-9.5 defines the backend enterprise release gate. The gate does not introduce new academic behavior. It aggregates existing readiness, integrity, durability, and configuration signals into a bounded operator report.

## Scope

The gate reports on:

- security and production configuration posture;
- durable event reliability and backlog health;
- learning journey release readiness;
- learning experience release readiness;
- runtime dependency posture at a high level;
- request correlation support for diagnosis.

## Canonical operator command

Use:

```text
python manage.py report_backend_release_gate
```

The command prints a JSON report with:

- `result`
- `blockers`
- `warnings`
- `summary`

Optional flag:

- `--fail-on-not-ready`

## Result meanings

- `READY`: no blockers or warnings.
- `READY_WITH_WARNINGS`: no blockers, but recoverable operational warnings exist.
- `NOT_READY`: one or more blockers exist.

## Gate interpretation

The gate is a release signal, not a product verdict.

Typical blocker examples:

- production-secret misconfiguration;
- missing required backend app installation;
- terminal durable-event failures;
- any domain readiness service reporting `NOT_READY`.

Typical warnings:

- durable event backlog present;
- debug mode enabled;
- domain readiness services reporting warnings;
- dependency posture that is operationally acceptable but worth monitoring.

## Release policy

- The gate must fail closed on credible present risk to security, tenant isolation, privacy, academic truth, data integrity, idempotency, concurrency, async reliability, migration correctness, or operational recovery.
- The gate must not invent new authority over academic state.
- The gate must not claim tests have passed.

