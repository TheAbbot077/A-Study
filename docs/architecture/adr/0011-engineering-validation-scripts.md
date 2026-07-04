# Engineering Validation Scripts

## Status
Accepted

## Context

Abbot Study needs repeatable, explicit commands for common validation and Docker maintenance tasks. These workflows should be safe, simple, and rooted in the existing Docker Compose environment rather than local ad hoc setup.

## Decision

We will add PowerShell scripts for backend validation, frontend validation, full validation, Docker reset, and log collection. The scripts will use Docker Compose as the authoritative runtime and will fail loudly if a command fails.

## Consequences

- Team members can run the same validation steps consistently.
- Validation remains container-based and avoids local environment drift.
- Scripts are explicit and repeatable, but they are not a replacement for deliberate developer judgment.
