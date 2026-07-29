# Learning Journey API

Base path:

```text
/api/learning-journeys/
```

## Endpoints

```text
GET /api/learning-journeys/
GET /api/learning-journeys/{journey_id}/
POST /api/learning-journeys/self-study/
POST /api/learning-journeys/institutional/
POST /api/learning-journeys/{journey_id}/synchronize/
POST /api/learning-journeys/{journey_id}/pause/
POST /api/learning-journeys/{journey_id}/resume/
POST /api/learning-journeys/{journey_id}/withdraw/
```

There is no generic status mutation endpoint.

## Self-study creation

Request:

```json
{
  "workspace_id": "..."
}
```

The service validates workspace ownership, prevents duplicate active journey roots for the same workspace, binds the journey to the workspace, synchronizes from authoritative self-study state, and returns a read-safe journey projection.

## Read contract

Responses include:

```json
{
  "journey_id": "...",
  "journey_type": "SELF_STUDY",
  "state": "DISCOVERING_GOAL",
  "status_reason": {
    "code": "INTENT_NOT_CONFIRMED"
  },
  "current_step": {
    "code": "DISCOVER_GOAL",
    "title": "Tell Abbot what you want to study",
    "description": "Start or continue a guided setup conversation.",
    "sequence": 10
  },
  "subject": null,
  "authority": null,
  "available_actions": [],
  "blockers": [],
  "capability_references": {},
  "version": 1
}
```

Clients should render this contract rather than reconstructing workflow state from separate self-study, diagnostic, teaching, and evidence endpoints.

## Read and synchronization policy

PI-8B.1 read services return a computed read projection from authoritative source records.

`POST /synchronize/` persists the computed state onto the journey aggregate, updates capability references, and emits state-change events when the meaningful state changes.

This keeps ordinary reads useful while preserving an explicit command for durable workflow synchronization.
