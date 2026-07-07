# Phase 3E Decision: Resource Ingestion Platform

## Status
Accepted

## Context
The academic capability needed a simple, architecture-first ingestion lifecycle for learning resources. The goal was to track ingestion work and publish lifecycle events without introducing a full parser or worker system.

## Decision
A new ResourceIngestionJob model and service were introduced under the academic app. The model records the linked learning resource, optional stored file, request source, requesting user, status, metadata, and timestamps. A dedicated service manages lifecycle transitions and publishes domain events.

## Consequences
- The platform can track ingestion progress in a consistent way.
- Future ingestion workers can build on the same lifecycle contract.
- The model remains intentionally lightweight and does not perform content parsing itself.
