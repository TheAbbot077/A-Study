# Core Durable Event Platform

PI-9.3 hardens the Abbot Study event backbone by persisting event intent before any broker scheduling occurs.

## Canonical flow

1. A domain service publishes a `BusinessEvent`.
2. The core publisher persists a `BusinessEventRecord` and per-consumer `BusinessEventDelivery` rows inside the same transaction.
3. After commit, a sweep task is scheduled on a best-effort basis.
4. The sweep claims pending deliveries and dispatches them idempotently.
5. Delivery state remains durable even if the broker or worker is unavailable.

## Safety rules

- Persist only identifier-oriented, sanitized payload data.
- Do not store raw transcripts, notes, answers, tokens, or file bodies in the ledger.
- Treat delivery rows as the source of truth for retry and terminal failure state.
- Keep consumer keys stable and explicit.

## Operator boundary

- Event ledger inspection belongs to admin, integrity checks, and release-readiness tooling.
- Ordinary learner-facing APIs do not expose the event ledger.
