# Storage Provider Abstraction

## Status
Accepted

## Context

We need a clean abstraction for storing files that keeps domain logic separated from provider implementations. Initial needs require a local filesystem provider for development while allowing future remote providers.

## Decision

Introduce a `StorageProvider` abstraction with methods for `upload`, `download`, `delete`, `exists`, and `generate_url`. Implement a `LocalStorageProvider` that writes to Django's `MEDIA_ROOT`. Provide a `StorageService` that uses a provider and publishes `storage.file_uploaded` and `storage.file_deleted` events via the Event Platform.

## Consequences

- Providers remain replaceable without changing application logic.
- Storage can publish events while avoiding decisions about downstream consumption.
- No external integrations are introduced in this phase.
