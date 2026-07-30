# Learning Journey Legacy Backfill

`LearningJourneyBackfillService` and `backfill_learning_journeys` inspect legacy records that do not yet have a learning journey.

Initial supported source:

- self-study workspaces.

Safety guarantees:

- dry-run by default;
- bounded `--limit`;
- optional `--tenant-id`;
- explicit `--execute` required for writes;
- no evidence, mastery, diagnostic, curriculum, or institutional authority fabrication;
- failures are isolated and reported by source identifier.

