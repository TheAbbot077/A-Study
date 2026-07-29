# Learning Journey Integrity

`LearningJourneyIntegrityService` detects cross-context inconsistencies and records durable `LearningJourneyIntegrityFinding` rows without duplicating open findings.

Initial checks include:

- missing source binding
- duplicate active subject binding
- institutional journey without assignment authority
- self-study journey with institutional-only authority
- terminal journey with active operation
- stale projection

Findings use severity values `INFO`, `WARNING`, `BLOCKING`, and `CRITICAL`, and states `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, and `DISMISSED`.

Integrity findings are operational diagnostics. Learner-facing blockers should translate them into safe product language.

