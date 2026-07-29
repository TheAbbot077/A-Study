# Learning Journey Error Contract

Journey APIs return stable error envelopes for operational failures:

```json
{
  "error": {
    "code": "JOURNEY_VERSION_CONFLICT",
    "message": "Journey version is stale.",
    "details": {},
    "recoverable": true,
    "resolution_action_code": ""
  }
}
```

Stable codes include validation errors, permission denial, not found, action unavailable, journey version conflict, idempotency payload mismatch, source-capability failure, and integrity/recovery failures.

HTTP mapping follows project conventions:

- `200`: successful read, no-op, or completed command
- `201`: created journey
- `202`: accepted long-running operation where supported
- `400`: invalid payload or failed command
- `401`: unauthenticated
- `403`: authenticated but unauthorized
- `404`: visible journey/resource not found
- `409`: version, state, operation, idempotency conflict, or recognized action unavailable under current journey policy
- `422`: reserved for future semantic-validation use if the project adopts it consistently
- `500`: unexpected operational failure

Raw Python exception text is not part of the public contract.
