# Learning Journey Operational API

PI-8B.5 adds a canonical operational surface over the existing journey engine. Capability APIs remain authoritative for detailed domain work; journey APIs coordinate product workflow.

Core endpoints:

- `GET /api/learning-journeys/`
- `GET /api/learning-journeys/active/`
- `GET /api/learning-journeys/{journey_id}/`
- `GET /api/learning-journeys/{journey_id}/progress/`
- `GET /api/learning-journeys/{journey_id}/activity/`
- `GET /api/learning-journeys/{journey_id}/actions/`
- `POST /api/learning-journeys/{journey_id}/actions/{action_code}/`
- `GET /api/learning-journeys/{journey_id}/operations/{operation_id}/`
- `GET /api/learning-journeys/{journey_id}/integrity/`
- `POST /api/learning-journeys/{journey_id}/recover/`

The canonical journey detail response includes journey identity, status, status reason, authority, learner, subject, current step, progress, active context, available actions, blockers, recent activity, and operational metadata. Compatibility fields such as `state`, `capability_references`, and `active_capabilities` remain available while clients migrate.

Reads report projection freshness; ordinary reads do not advance learning state. Synchronization remains explicit through service-backed commands.

