# Learning Journey Idempotency

The idempotency contract is:

```text
same journey + same action + same idempotency key + same safe payload hash
→ same receipt semantics
```

Different payloads with the same key are rejected as a conflict. Safe request metadata stores hashes and allowlisted values only; raw learner content is not stored in receipts.

Read endpoints are idempotent and non-mutating with respect to learning policy state.

