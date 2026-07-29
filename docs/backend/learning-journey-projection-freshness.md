# Learning Journey Projection Freshness

Journey reads expose:

- `projection_version`
- `journey_version`
- `last_synchronized_at`
- `stale`
- `synchronization_required`
- `etag`

Freshness policy:

- synchronize after successful journey commands;
- synchronize after explicit operational recovery;
- allow event handlers to synchronize derived state in later increments;
- avoid hidden write-on-read behavior for ordinary reads.

Synchronization may emit journey events. Event-driven handlers must be idempotent and avoid recursive source mutation loops.

