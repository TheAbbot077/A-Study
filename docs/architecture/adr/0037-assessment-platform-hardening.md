# ADR 0037: Assessment Platform Hardening

## Status

Accepted.

## Context

PI-5A through PI-5I delivered the complete Evidence of Learning Platform, but the increment still contained engineering inconsistencies typical of an actively expanding system:

* mixed error semantics
* inconsistent lifecycle failure handling
* uneven API failure translation
* avoidable query inefficiencies
* incomplete operational documentation

The platform needed a dedicated hardening increment before becoming the stable foundation for future evidence sources.

## Decision

Use PI-5J as a production-readiness hardening increment.

Apply targeted improvements that preserve behavior:

* shared domain-oriented exception types
* stronger lifecycle and validation guards
* API translation of predictable domain failures into `400` responses
* lightweight operational logging
* admin consistency improvements
* updated canonical PI-5 architecture documentation

Do not redesign stable capabilities solely for architectural purity.

## Consequences

The platform becomes easier to operate, reason about, and extend without forcing a disruptive rewrite.

Earlier assessment services remain more ORM-centric than later PI-5 capabilities, but their failure behavior and lifecycle protections are stronger and more consistent.

Future increments can adopt repository abstractions more broadly if justified by new complexity, rather than as a retroactive cleanup exercise disconnected from product value.

## Non-Goals

PI-5J does not implement:

* new evidence product features
* AI evaluation
* remediation redesign
* review-platform redesign
* frontend dashboards
* breaking API changes
