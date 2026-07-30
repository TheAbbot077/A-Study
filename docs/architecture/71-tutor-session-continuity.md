# 71. Tutor Session Continuity

PI-7C.1 adds a deterministic opening context for the learner-facing Abbot Learning Studio.

The opening is a projection over existing governed authorities. It does not create a new teaching, curriculum, diagnostic, plan, memory, or mastery authority.

## Backend contract

The workspace API exposes:

`GET /api/self-study/workspaces/{workspace_id}/tutor-session-opening/`

The response includes:

- `readiness`: `READY`, `PARTIAL`, or `BLOCKED`;
- `opening_message`: deterministic learner-safe copy;
- `workspace_summary`: display name, workspace status, safe goal, and target title;
- `current_destination`: the current teaching-session node or first governed bridge-plan node when available;
- `previous_activity_summary`: optional learner-visible, mentor-eligible memory;
- `safe_identity_summary` and `mentor_memory_items`: learner-safe Learning Identity context;
- `next_action`: backend-authoritative continuation target;
- `guardrails`, `omitted_context`, `blocker_codes`, and `warning_codes`.

## Authority boundaries

The service composes:

- PI-6F.9 workspace ownership and lifecycle;
- PI-6F.10 study-plan state;
- PI-6F.11 Learning Studio readiness;
- PI-7B Learning Identity mentor-context memory.

It never:

- starts a teaching session;
- advances a plan;
- infers mastery, ability, learning style, disability, motivation, or diagnosis;
- exposes raw diagnostic answers, scores, resolver internals, hidden provenance, source corpora, or contested memory;
- treats uploaded documents or learner messages as instructions.

## Readiness behavior

`READY` means a governed teaching destination exists and the Learning Studio has no active blockers.

`PARTIAL` means a safe destination or memory context can be shown, but teaching continuity still has recoverable blockers such as pending preparation.

`BLOCKED` means the workspace lacks a governed destination or has stale/invalid authority such as a stale plan or invalidated learning session.

Historical sparse memory is not blocking. Missing Learning Identity memory produces a warning, not an error.

## Frontend behavior

The Learning Studio route displays a Session continuity card above the teaching stream. It shows:

- Abbot’s deterministic welcome;
- today’s focus;
- last learner-approved activity when available;
- the learner’s safe goal;
- blocker state when backend readiness is not ready;
- a guarded start/resume/continue action.

The frontend renders backend state only. It does not invent prior activity, plan progress, readiness, or learner traits.

## Manual validation

Suggested validation commands:

```powershell
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend pytest apps/self_study/tests/test_tutor_session_continuity.py -q
docker compose exec backend pytest apps/self_study
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
docker compose exec frontend npm run smoke:audit
docker compose exec frontend npx playwright test tests/smoke/self-study-workspace-view-model.spec.ts --project=chromium
docker compose exec frontend npm run smoke:e2e
```
