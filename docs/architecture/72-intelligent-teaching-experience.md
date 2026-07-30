# 72. Intelligent Teaching Experience

PI-7C completes the first governed intelligent-teaching foundation for Abbot Learning Studio.

The capability turns the studio from a static shell into a structured tutor-led experience while preserving the authority boundaries established by PI-6F, PI-7A, and PI-7B.

## What it does

The backend exposes a cohesive Learning Studio session projection:

- tutor session opening;
- ordered teaching runtime steps;
- explanation modes;
- Socratic prompt response receipts;
- structured whiteboard artifacts;
- concept-check response receipts;
- session closure and micro-victory copy.

The first implementation is deterministic and template-driven. It does not require an LLM.

## API surface

Workspace-scoped endpoints:

- `GET /api/self-study/workspaces/{workspace_id}/learning-studio/session/`
- `POST /api/self-study/workspaces/{workspace_id}/learning-studio/session/start/`
- `POST /api/self-study/workspaces/{workspace_id}/learning-studio/session/explanation-mode/`
- `POST /api/self-study/workspaces/{workspace_id}/learning-studio/session/respond/`
- `POST /api/self-study/workspaces/{workspace_id}/learning-studio/session/complete/`

All endpoints enforce the existing workspace ownership and tenant boundary through the workspace viewset.

## Runtime steps

The runtime projects a governed destination into ordered steps:

1. opening;
2. recap;
3. teach;
4. example;
5. whiteboard;
6. Socratic prompt;
7. concept check;
8. summary;
9. next step.

If the governed destination is missing or stale, the runtime fails closed with blocked steps.

## Explanation modes

Supported presentation modes:

- simple;
- visual;
- academic;
- exam-focused;
- analogy;
- examples;
- mathematical.

Explanation modes change presentation only. They do not create new curriculum, subjects, competencies, or academic claims.

## Socratic prompts and concept checks

Socratic and concept-check responses produce learner-safe receipts.

When an existing teaching session is awaiting a learner and the request supplies the required idempotency/version data, the response delegates to the existing governed teaching-turn recorder. Otherwise, the response remains a bounded interaction receipt.

These receipts do not award mastery, credit, grades, or credentials.

## Whiteboard foundation

The first whiteboard artifact is structured data, not raw SVG or generated imagery. It supports learner-safe concept-map rendering with nodes, edges, and rendering hints.

The artifact is a teaching aid. It is not a source of academic authority.

## Session closure

Closure answers:

- what was worked on;
- what the learner can now try;
- what comes next;
- what guardrails apply.

Micro-victory copy is deliberately modest and does not imply mastery.

## Learning Identity boundary

PI-7C reads learner-safe mentor context through PI-7B. It does not mine raw teaching transcripts, infer durable traits, or write raw responses into Learning Identity.

Future systems may summarize governed evidence through provenance-aware paths, but this runtime does not infer identity from learner text.

## What it does not own

PI-7C does not:

- create curriculum or subjects;
- mutate bridge plans;
- alter diagnostic placement;
- create official assessments;
- award mastery;
- implement Ariel Teach-Back;
- simulate exams;
- expose resolver scores, rejected candidates, raw diagnostic data, or governance internals.

## Preparation for PI-8

PI-7C creates the learner-facing teaching substrate that Ariel can later use for teach-back evidence. Ariel should build on these governed session, prompt, whiteboard, concept-check, and closure contracts without becoming an official examiner.
