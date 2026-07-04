# Storage Platform

## Purpose

Storage is a reusable platform capability that owns file storage concerns for Abbot Study. It manages how files are stored and retrieved but does not own Document-level business logic.

## What Storage Owns

- The `StoredFile` domain model describing stored artifacts
- Provider abstractions for interchangeable storage backends
- The `LocalStorageProvider` implementation for development
- The `StorageService` application service
- Publishing storage lifecycle events (`storage.file_uploaded`, `storage.file_deleted`)

## What Storage Does Not Own

- Document semantics or associations
- PDF or textbook-specific processing
- Virus scanning or image processing
- External provider integrations (S3/R2) in this phase

## Concepts

- Provider: implements the storage primitives (`upload`, `download`, `delete`, `exists`, `generate_url`).
- Service: coordinates provider use and application-level concerns, including model creation and event publishing.
- Event: business events are published after successful operations; storage does not decide who consumes them.

## Why Local First

A local provider simplifies development and testing. Providers are pluggable and can be swapped for remote providers later.
