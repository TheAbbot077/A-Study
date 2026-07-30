# Learning Journey Event Reliability

Journey events are registered in the shared core event registry and emitted with identifier-only payloads.

Required event groups:

- lifecycle: created, synchronized, state changed, paused, resumed, withdrawn, archived;
- actions: accepted, succeeded, failed, rejected, command conflicted;
- operations: started, completed, failed;
- integrity and recovery: finding detected, finding resolved, recovery started, recovery completed;
- competency and plan evolution: learning competency events, journey evolved, learning plan evolution requested;
- institutional: assigned, accepted, activated, completion ready/completed, intervention created/resolved.

Events are observational unless explicitly documented by the handling service. Synchronization events must not trigger source mutations that produce recursive loops.

