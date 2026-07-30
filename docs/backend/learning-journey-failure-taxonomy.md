# Learning Journey Failure Taxonomy

Public operational failures use stable categories:

- `AUTHENTICATION_FAILURE`
- `AUTHORIZATION_FAILURE`
- `VALIDATION_FAILURE`
- `AUTHORITY_FAILURE`
- `STATE_CONFLICT`
- `VERSION_CONFLICT`
- `IDEMPOTENCY_CONFLICT`
- `ACTIVE_OPERATION_CONFLICT`
- `SOURCE_CAPABILITY_REJECTION`
- `SOURCE_CAPABILITY_FAILURE`
- `SYNCHRONIZATION_FAILURE`
- `PROJECTION_STALE`
- `INTEGRITY_FAILURE`
- `RECOVERY_REQUIRED`
- `TRANSIENT_INFRASTRUCTURE_FAILURE`
- `UNEXPECTED_FAILURE`

APIs expose stable error envelopes and action receipt failure codes. Raw exception class names are for internal logs only and are not public API contracts.

