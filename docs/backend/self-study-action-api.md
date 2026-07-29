# Self-study journey action API

PI-8B.2 adds:

```http
POST /api/learning-journeys/{journey_id}/actions/{action_code}/
```

Request:

```json
{
  "idempotency_key": "client-generated-key",
  "payload": {}
}
```

Response:

```json
{
  "receipt": {
    "id": "uuid",
    "action_code": "BEGIN_GOAL_DISCOVERY",
    "status": "SUCCEEDED",
    "failure_code": "",
    "failure_message": "",
    "replayed": false
  },
  "journey": {
    "journey_id": "uuid",
    "state": "DISCOVERING_GOAL",
    "current_step": {},
    "available_actions": [],
    "blockers": [],
    "progress": {},
    "active_capabilities": {}
  }
}
```

Action codes may be supplied as kebab-case in the URL and are normalized to backend action codes.

The endpoint enforces authenticated actor identity, journey readability, self-study journey type, source workspace ownership, action policy, and payload-level preconditions.
