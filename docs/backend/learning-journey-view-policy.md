# Learning Journey View Policy

PI-8B.5 centralizes actor-specific journey visibility in `LearningJourneyViewPolicy`.

Supported view roles:

- learner
- institutional educator
- institutional administrator
- platform administrator

Learners see current step, next actions, progress, recoverable blockers, and safe authority context. Institutional educators see institution-visible progress summaries, interventions, and completion readiness. Institutional administrators also see assignment authority and operational metadata. Platform administrators may inspect operational state, but private learner content is still minimized by default.

The policy excludes raw mentor memory, private notes, private diagnostic responses, raw evidence bodies, and internal implementation details from ordinary operational views.

