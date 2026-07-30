# Learning Journey End-to-End Scenarios

PI-8B.6 introduces deterministic backend scenario fixtures in `apps/learning_journeys/tests/scenarios/`.

Covered scenario chains:

- self-study workspace → journey → operational view;
- evidence → mastery decision → competency progression → journey evolution;
- institutional assignment → shared journey → competency progression → completion readiness;
- rejected action → receipt → operation history;
- stale projection → integrity finding → safe recovery;
- legacy self-study workspace → dry-run/explicit backfill.

The tests deliberately use the same journey, evidence, mastery, competency progression, and operational view services for self-study and institutional authority. They do not introduce parallel institutional teaching, evidence, mastery, or progression engines.

