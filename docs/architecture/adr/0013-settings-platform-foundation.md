# Settings Platform Foundation

## Status
Accepted

## Context

Abbot Study needs a reusable settings capability that can support both user-level and institution-level preferences without tying the logic to business-specific domains. The platform must preserve typed values and publish events when settings change.

## Decision

We will introduce a Settings Platform in the backend with domain models for UserSetting and InstitutionSetting, a SettingsService for typed persistence and retrieval, and business event publication for create/update/delete operations.

## Consequences

- Settings become a reusable capability available to future domains.
- Value types are preserved through serialization and deserialization.
- The platform remains intentionally simple and excludes UI, caching, and feature-flag behavior.
