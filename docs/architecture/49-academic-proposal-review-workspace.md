# Academic Proposal Review Workspace (PI-6E.2)

Status: implemented, awaiting manual Docker validation.

## Scope and route

PI-6E.2 implements the protected reviewer workspace at:

`/dashboard/academic-review/:proposalId`

It opens or resumes the current PI-6D.1 review session, displays the backend-returned outline, findings, evidence, summary, version, and lifecycle, and allows only the review commands registered by the backend. The route retains resource context through its heading, source label, and link back to `/dashboard/resources/:resourceId`.

The capability ends when the backend returns `ready_for_approval`. It does not approve or reject at the approval boundary, create an approved projection, populate Academic content, synchronize retrieval, or evaluate teaching readiness.

## Authority and state ownership

The backend owns lifecycle, permissions, review decisions, finding resolution, summary counts, and completion readiness. The frontend never derives an authoritative readiness decision.

State is separated into:

- server state: the last confirmed session, outline, findings, and selected-item evidence;
- local editor state: title, ordering, and note fields for the selected item only;
- UI state: selection, finding filters, dialogs, notices, and expanded evidence.

Every successful command is followed by an authoritative session, outline, and findings refresh. Failed commands preserve the selected editor input. Selection or refresh with unsaved input requires deliberate discard confirmation.

## Supported workflow

The workspace uses these PI-6D.1 endpoints:

- `POST /api/academic-review/sessions/proposals/{proposal_id}/start/`
- `GET /api/academic-review/sessions/{session_id}/`
- `GET /api/academic-review/sessions/{session_id}/outline/`
- `GET /api/academic-review/sessions/{session_id}/findings/`
- `GET /api/academic-review/sessions/{session_id}/items/{decision_id}/evidence/`
- `POST /api/academic-review/sessions/{session_id}/items/{decision_id}/decide/`
- `POST /api/academic-review/sessions/{session_id}/items/{decision_id}/edit/`
- `POST /api/academic-review/sessions/{session_id}/resolve-finding/`
- `POST /api/academic-review/sessions/{session_id}/submit/`

Supported item commands are include, exclude, title edit, ordering edit, and review note submission. Finding resolution uses only the registered `rejection`, `edit`, and `move` actions; administrator override is deliberately absent from this workspace.

Evidence is read-only and progressively disclosed. It shows reviewer-useful page ranges, hierarchy, evidence strength, confidence, excerpt, and stable evidence reference without exposing storage paths or internal credentials.

## Lifecycle, concurrency, and idempotency

`in_progress` is editable. `ready_for_approval` is displayed as completed and read-only. Approved, rejected, reprocessing-requested, superseded, and abandoned sessions are also read-only with explicit explanations.

The PI-6D.1 decision, edit, finding-resolution, and submit serializers do not accept an expected session version or idempotency key. The frontend therefore does not invent transport fields. It disables the active command, displays normalized conflicts, preserves local input after failure, and requires deliberate refresh. Adding backend concurrency and replay protection to these commands remains a transport-contract hardening opportunity.

## Completion and accessibility

Completion is enabled only when the backend session summary reports `ready: true` while the lifecycle is `in_progress`. The confirmation dialog displays backend-derived counts and explains that completion is not approval or publication.

The workspace uses semantic headings and navigation, labeled controls, textual status/severity, visible focus styles, `aria-current`, live status regions, native modal-dialog behavior, keyboard-operable controls, responsive stacked layouts, and overflow-safe evidence.

## Manual validation

```powershell
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
docker compose exec frontend npm run smoke:audit:test
docker compose exec frontend npm run smoke:audit
docker compose exec frontend npm run smoke:e2e
```
