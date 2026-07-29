# Learning Journey Operation Contract

`LearningJourneyOperation` is the stable polling and operational visibility record for journey commands and future long-running workflows.

Statuses:

- `PENDING`
- `RUNNING`
- `SUCCEEDED`
- `FAILED`
- `CANCELLED`

Operations reference the journey, action code, actor, optional receipt, safe phase, failure code, and result reference. They do not contain raw transcripts, diagnostic answers, or private learner memory.

`GET /api/learning-journeys/{journey_id}/operations/{operation_id}/` returns operation status, linked receipt, and the updated journey representation when the operation is terminal.

