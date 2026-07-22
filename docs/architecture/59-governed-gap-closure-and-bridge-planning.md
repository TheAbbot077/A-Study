# Governed gap closure and prerequisite bridge planning

PI-6F.6 extends the `self_study` bounded context with a deterministic, governed bridge between curriculum selection/diagnosis/coverage and PI-6F.7 delivery planning. It does not teach, infer mastery, acquire resources, or mutate upstream authority.

## Authority and frozen inputs

A `BridgePlanningRun` freezes the tenant and intent, curriculum selection, exact published graph version and fingerprint, authorized target set, privacy-safe diagnostic placement fingerprint, completed coverage evaluation and gap-set fingerprint, and planning/applicability/approval policy versions. Canonical sorted serialization produces the run and component fingerprints; timestamps, task identifiers, raw diagnostic answers, source text, and temporary locations are excluded.

Targets must be nodes in the intent's current published graph and an authorized target type. Prerequisite closure follows only authoritative PI-6F.3 `REQUIRES` edges. In that graph, the source is the dependent and the target is its prerequisite; bridge dependencies retain the exact edge while ordering prerequisite before dependent. Shared prerequisites are deduplicated, cycles and dangling edges block generation, and deterministic order is topology, graph ordinal, then stable key.

## Two governed axes

Each immutable plan node stores a learner-path disposition and an independent material-feasibility disposition. `MATERIAL_BLOCKED` and `CONFLICT_BLOCKED` therefore are represented by `MATERIAL_MISSING` and `MATERIAL_CONFLICTING` on the material axis rather than collapsing material state into the learner axis. A diagnostic `DEMONSTRATED` classification can reduce the learning path to reinforcement, but explicitly carries a no-mastery-assertion rationale. Uncertain, unassessed, and non-waivable prerequisites remain visible.

PI-6F.5 coverage is overlaid, never recalculated. Covered, partial, missing, conflicting, unevaluated, supplementary-only, out-of-scope, and applicability-mismatched states map to stable feasibility findings. Only the permitted citation-set fingerprint is copied into the plan.

## Lifecycle, workers, and governance

The asynchronous sequence is:

1. `self_study.create_bridge_plan` claims an identifier-only pending run, resolves graph closure, overlays placement and coverage, and persists a complete proposed plan atomically.
2. `self_study.finalize_bridge_plan` verifies persisted results and exposes either `READY_FOR_REVIEW` or `BLOCKED`.
3. Reviewers separately approve or reject. Approval of a blocked plan may acknowledge it but does not change its blocked status.
4. Activation requires an approved, current, unblocked plan and transactionally supersedes the previous active plan for the same intent and target-set fingerprint.

Graph, diagnostic, coverage/gap-set, applicability, planning-policy, and algorithm changes are handled through `MarkBridgePlansStaleService`. Historical plans remain immutable and stale/invalidated plans cannot be handed to PI-6F.7.

Events are identifier-only and emitted after commit: `self_study.bridge_planning_run.created`, `self_study.bridge_plan.generated`, `.blocked`, `.approved`, `.rejected`, `.activated`, `.stale`, `.invalidated`, `.superseded`, and `.failed`.

## API

Tenant-scoped DRF routes expose planning-run creation/list/detail, plan detail, paginated nodes/dependencies/findings, approve/reject/activate/invalidate/recalculate commands, and the current PI-6F.7 handoff. Learners may read their own context; institutional authority is required for governed commands. Responses never contain diagnostic responses or unrestricted evidence text.

The handoff contains only the current active plan fingerprint, exact graph and upstream fingerprints, targets, ordered learner/material dispositions, traceable dependencies, blockers, permitted citation references, and policy/algorithm versions. It rejects inactive, blocked, stale, invalidated, or upstream-mismatched plans.

## Validation

Validation is manual in Docker after review. Run Django checks and migration drift checks, targeted PI-6F.6 tests, all `self_study` tests, the backend suite, route-contract/audit checks, and Celery task discovery. This document does not claim those checks have passed.

```text
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend pytest apps/self_study/tests/test_bridge_planning_domain.py apps/self_study/tests/test_bridge_planning_tasks.py apps/self_study/tests/test_bridge_planning_routes.py
docker compose exec backend pytest apps/self_study/tests
docker compose exec backend pytest
docker compose exec frontend npm run smoke:audit:test
docker compose exec frontend npm run smoke:audit
docker compose exec celery celery -A config inspect registered
```
