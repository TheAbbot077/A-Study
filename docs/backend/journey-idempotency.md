# Journey idempotency

Journey actions use:

```text
journey id + action code + idempotency key
```

as the durable idempotency identity.

If a matching receipt already exists in a terminal receipt status (`SUCCEEDED`, `NO_OP`, or `REJECTED`), the orchestrator returns the existing receipt and current journey projection instead of executing the source command again.

Source services that already provide idempotency keep their authority. The journey receipt prevents duplicate orchestration delivery; the source capability prevents duplicate domain effects.

Sensitive payloads are not stored in receipts. Only safe metadata keys are retained.
