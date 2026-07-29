# Journey action receipts

`LearningJourneyActionReceipt` records every externally executable journey action attempt.

Receipt statuses:

- `ACCEPTED`
- `SUCCEEDED`
- `FAILED`
- `REJECTED`
- `NO_OP`

Receipts store:

- journey id;
- action code;
- actor id;
- idempotency key;
- source capability;
- source record id;
- safe request metadata;
- safe result metadata;
- failure code and message when applicable.

Receipts must not store raw diagnostic answers, tutor transcripts, or hidden scoring/provenance internals.
