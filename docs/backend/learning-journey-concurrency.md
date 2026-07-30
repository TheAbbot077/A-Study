# Learning Journey Concurrency

Journey commands use:

- optimistic version checks through `expected_journey_version`;
- idempotency keys and payload hashes;
- immutable source bindings;
- uniqueness constraints for source binding, active subject binding, competency progress, and idempotent action receipts;
- operation records for accepted/completed/failed command visibility.

Stale commands return `JOURNEY_VERSION_CONFLICT`. Reusing an idempotency key with a materially different payload returns `IDEMPOTENCY_KEY_PAYLOAD_MISMATCH`.

