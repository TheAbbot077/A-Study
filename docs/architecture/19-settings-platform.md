# Settings Platform

## Purpose

The Settings Platform provides reusable, typed settings storage for users and institutions. It is designed as a platform capability independent of any single business domain.

## What the Settings Platform Owns

- typed user settings
- typed institution settings
- serialization and deserialization of values
- event publication for setting changes and deletions

## What It Does Not Own

- feature flags
- notification preferences UI
- user-facing settings screens
- caching
- domain-specific learning preferences

## Domain Model Notes

UserSetting and InstitutionSetting store values by key and preserve a stable value type so settings can be round-tripped safely.

## Event Model

The Settings Platform publishes events when settings are created, updated, or deleted. Consumers are intentionally decoupled from the platform and may react independently.
