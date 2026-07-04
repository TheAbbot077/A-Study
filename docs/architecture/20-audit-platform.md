# Audit Platform

## Purpose

The Audit Platform provides a reusable capability for recording meaningful actions across Abbot Study. It captures actor, institution, action, target, and metadata without coupling to any one business domain.

## What the Audit Platform Owns

- the AuditEntry domain model
- persistence for audit records
- an AuditService for recording and querying actions
- event publication for audit creation

## What It Does Not Own

- analytics dashboards
- retention policies
- notification integration
- admin UI features

## Design Notes

Audit entries are intentionally lightweight. They support later analytics or compliance workflows while remaining independent of delivery or presentation concerns.
