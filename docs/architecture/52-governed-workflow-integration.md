# PI-6E.5 Governed Workflow Integration

Status: implemented and awaiting manual validation.

PI-6E.5 consolidates the existing frontend capabilities into one presentation-only
workflow:

`UPLOAD → PROCESSING → REVIEW → APPROVAL → POPULATION → RETRIEVAL → TEACHING READINESS`

The workflow mapper is pure and deterministic. It translates existing backend
transport state into accessible presentation states without persisting an overall
status or calculating backend eligibility. Unknown backend values are shown as
blocked, with the unknown value visible; they are never treated as complete.

The same semantic timeline is used on resource detail, proposal review, and
governance operations. Links are included only where the required route identifier
already exists. The timeline does not execute mutations.

## Canonical distinctions

- READY_FOR_REVIEW is not READY_FOR_POPULATION.
- READY_FOR_POPULATION is not SYNCHRONIZED.
- SYNCHRONIZED is not READY_FOR_TEACHING.
- READY_FOR_TEACHING does not necessarily mean learner-published.

User-facing readiness language is qualified as ready for review, ready for
approval, ready for population, ready for synchronization, or ready for teaching.
Processing percentages are described as processed progress and do not imply
publication or readiness.

## Refresh, polling, and recovery

Review refresh preserves the selected item and confirms before discarding unsaved
input. Governance and operational refreshes retain their last authoritative state
when a subsequent request fails. Retrieval polling reuses the shared serial polling
primitive and stops on terminal success, terminal failure, unmount, or identifier
change. Governed mutation idempotency keys remain scoped by resource and operation;
uncertain failures do not retire the key.

Stale readiness removes ready emphasis and retains the historical evaluation.
Failures display backend codes, safe messages, retry eligibility, and correlation
references where supplied. No retry route or permission is inferred.

## Accessibility and responsive behavior

The timeline is a labelled navigation landmark with an ordered stage list,
programmatic current-step state, textual status, blocker and warning counts,
keyboard-operable links, visible focus, and responsive card grids. Identifiers wrap,
dialogs remain native modal dialogs, and operational lifecycle updates use live
regions.

## Manual validation

```powershell
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
docker compose exec frontend npm run smoke:audit
docker compose exec frontend npm run smoke:audit:test
docker compose exec frontend npm run smoke:e2e
```

After successful manual validation, the user may mark PI-6E complete.
