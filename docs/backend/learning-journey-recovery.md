# Learning Journey Recovery

Recovery restores derived consistency. It never invents authority or bypasses learning policy.

Supported first recovery operation:

- synchronize stale journey projections when a source binding exists.

Forbidden recovery shortcuts:

- creating arbitrary subject bindings;
- marking competencies demonstrated;
- completing diagnostics;
- approving institutional completion;
- changing curriculum authority;
- deleting historical progression.

Recovery is available through `POST /api/learning-journeys/{journey_id}/recover/`, Django admin actions, and management commands.

