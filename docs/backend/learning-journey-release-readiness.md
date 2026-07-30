# Learning Journey Release Readiness

`LearningJourneyReleaseReadinessService` and `report_learning_journey_release_readiness` produce a deterministic system-state report. The report does not claim tests passed.

Results:

- `READY`: no blockers or warnings.
- `READY_WITH_WARNINGS`: no blockers, but recoverable operational warnings exist.
- `NOT_READY`: release blockers exist.

Blockers include:

- missing required events;
- open critical/blocking integrity findings;
- stuck operations beyond threshold;
- institutional journeys without authority;
- self-study journeys with institutional-only authority.

Warnings include:

- stale projections;
- active but not stuck operations;
- non-critical integrity findings;
- missing journey-adjacent task registrations;
- legacy records eligible for optional backfill.

