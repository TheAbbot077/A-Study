# Learning Journey Action Contract

Journey actions are discovered from the same policy used to execute them. The canonical view and `GET /actions/` expose visible actions only for the current actor.

Action fields:

- `code`
- `label`
- `description`
- `enabled`
- `disabled_reason`
- `requires_confirmation`
- `payload_schema`
- `execution_mode`

Mutating action requests use:

```json
{
  "idempotency_key": "uuid-or-client-key",
  "expected_journey_version": 12,
  "payload": {}
}
```

Results distinguish `SUCCEEDED`, `ACCEPTED`, `REJECTED`, `NO_OP`, `FAILED`, and `CONFLICT`. Idempotent retries with the same payload return the same receipt semantics. Reusing a key with a materially different payload returns `IDEMPOTENCY_KEY_PAYLOAD_MISMATCH`.

Action execution delegates to authoritative capability services. The journey orchestrator does not duplicate curriculum, diagnostic, teaching, mastery, or progression algorithms.

