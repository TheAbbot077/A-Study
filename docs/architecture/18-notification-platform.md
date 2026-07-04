# Notification Platform

## Purpose

The Notification Platform is a reusable capability for creating and delivering notifications without coupling to any specific channel or business domain.

## What the Notification Platform Owns

- the Notification domain model
- channel abstractions for interchangeable providers
- a NotificationService entry point
- event publication for notification lifecycle milestones

## What It Does Not Own

- real email delivery backends
- SMS, push, Slack, or Teams integrations
- frontend notification UI
- unsubscribe, preference, or template management

## Channel Abstraction

The platform uses a provider abstraction so that different channels can be swapped in without changing application services. The initial implementation uses a logging provider for in-process development.

## Why Real Email Is Out of Scope

The initial foundation focuses on structure and lifecycle behavior rather than production delivery. Real email infrastructure will be introduced later when the platform is ready for operational integration.

## Future Direction

Future iterations may add additional channels and event-driven consumers while keeping the core service boundary stable.
