# 65. Abbot Learning Studio

PI-6F.11 adds the learner-facing Abbot Learning Studio for self-study workspaces.

The studio is a product UI and workspace-scoped projection over PI-6F.8 governed teaching orchestration. It does not create a new teaching algorithm, curriculum authority, diagnostic authority, bridge-plan authority, concept-check scorer, or mastery service.

## Authority boundaries

- PI-6F.6 remains the authority for bridge-plan nodes and prerequisite order.
- PI-6F.7 remains the authority for teaching preparation, teaching packs, retrieval publication, and readiness.
- PI-6F.8 remains the authority for teaching sessions, current nodes, turns, citations, transitions, and evidence/mastery boundaries.
- PI-6F.11 renders the studio state and delegates learner commands to PI-6F.8.
- PI-6F.12 owns formal concept checks.

Teaching segment completion in the studio is not mastery, certification, credit, or a grade.

## Workspace-scoped API

The workspace ViewSet exposes finite learning-studio endpoints:

- `GET learn/experience/`
- `POST learn/start/`
- `POST learn/resume/`
- `POST learn/pause/`
- `GET|POST learn/turns/`
- `POST learn/turns/next/`
- `POST learn/recap/`
- `POST learn/review/`
- `GET learn/current-node/`
- `GET learn/progress/`
- `GET learn/citations/`

All endpoints enforce the existing workspace ownership/tenant boundary before delegating to teaching orchestration.

## Frontend experience

The `/dashboard/self-study/:workspaceId/learn` route now renders the Abbot Learning Studio:

- current concept header;
- study-plan progress;
- Abbot/learner turn stream;
- learner response input;
- start/resume/pause/recap/review controls;
- learner-safe source panel;
- blocked/stale state display;
- concept-check handoff placeholder.

The studio intentionally avoids “mastered”, “passed”, “certified”, and similar language.

## Source grounding

Citations are projected from PI-6F.8 `TeachingTurnCitation` records. The learner-facing citation view includes safe resource identity, page/segment labels where available, bounded excerpts, and source state. It does not expose diagnostic details, hidden prompts, raw corpora, or unsafe/internal provenance.

## Validation

Manual Docker validation should include Django checks, migration drift checks, targeted self-study tests, frontend typecheck/lint, route-contract tests, route audit, and smoke tests. This document does not claim validation has passed.
