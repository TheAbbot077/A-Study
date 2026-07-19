# Academic Proposal Review

PI-6D.1 introduces `academic_review` as the governance boundary between machine-generated PI-6C proposals and Academic Platform population.

## Invariants

- `AcademicImportProposal`, proposed items, evidence, confidence, and validation findings remain immutable machine records.
- A `ProposalReviewSession` snapshots the proposal version and checksum. Decisions, edits, finding resolutions, bulk actions, and overrides form an auditable overlay.
- Reviewers may accept, reject, rename, reorder, and move items. Concepts may only target accepted sections.
- Blocking findings require an explicit rejection, edit, move, or administrator override resolution before submission.
- Approval creates an immutable `ApprovedProposalProjection`. Population consumes only this projection and never raw proposed items.
- Rejected items never enter the projection. Reviewed titles, ordering, and placement are copied into it.
- Population dispatch occurs through `transaction.on_commit` and the existing asynchronous `POPULATING` stage.
- Reprocessing closes the review, supersedes its proposal, preserves all history, and creates a new processing attempt.

## Lifecycle

`NOT_STARTED → IN_PROGRESS → READY_FOR_APPROVAL → APPROVED | APPROVED_WITH_EDITS`

Active reviews may instead become `REJECTED` or `REPROCESS_REQUESTED`. `SUPERSEDED` and `ABANDONED` are terminal historical states.

## Permissions

Students have no review access. Institution reviewers may review items and submit. Institution administrators, owners, system administrators, staff, or superusers may approve and override. API services enforce authorization; the frontend only reflects those capabilities.

## Read models

The API exposes paginated/filterable session outlines, proposal summaries, evidence provenance, findings, and decision state. Evidence includes source pages, blocks, hierarchy, semantic segment references, confidence, and evidence strength; PDF rendering is intentionally deferred.

## Events and audit

Lifecycle changes, item decisions/edits, bulk actions, overrides, submission, approval, rejection, reprocessing, and population requests publish business events and durable audit entries. Temporary UI state is not audited.

## PI-6D.2 Reviewed Approval and Projection

Approval is a separate governed phase after review submission. An academic approver first creates a durable `ApprovalReadinessSnapshot` bound to the proposal checksum, proposal version, review-session version, and approval policy version. It records item counts, finding resolution, hierarchy and placement defects, canonical duplicates, overrides, reasons, and a deterministic snapshot checksum.

Approval locks the session and proposal, verifies the snapshot is current, rebuilds readiness, and rejects stale or blocked commands. Commands carry an idempotency key. Repository uniqueness and row locks ensure identical concurrent commands return one `ApprovalDecision` and one projection.

The immutable publication contract comprises:

- `ApprovedProposalProjection`, including approval version, resource scope, status, and projection/hierarchy/concept/provenance checksums;
- `ApprovedSection`, containing final and canonical titles, reviewed hierarchy, ordinal, depth, page range, evidence, decision, edit, and override provenance;
- `ApprovedConcept`, containing accepted placement, final and canonical titles, ordinal, source pages, supporting evidence, and review provenance.

Rejected items and heading-only concepts never enter this projection. Canonical duplicate titles, dotted leaders, page markers, invalid hierarchy, orphan concepts, unresolved blocking findings, superseded proposals, and newer proposal attempts block approval.

Successful approval ends at `READY_FOR_POPULATION` and publishes `academic_review.ready_for_population`. PI-6D.2 does not dispatch population, write Academic Platform records, index retrieval, or mark teaching readiness. PI-6D.3 is the sole consumer responsible for those transitions.
