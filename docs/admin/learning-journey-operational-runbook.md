# Learning Journey Operational Runbook

## Journey blocked

Diagnostic action: inspect the canonical journey view, blockers, active context, operations, and integrity findings.

Safe recovery: synchronize the journey; run integrity check; repair only derived stale projections.

Forbidden: fabricate subject bindings, mastery decisions, diagnostic completions, or institutional authority.

## Projection stale

Diagnostic action: run `check_learning_journey_integrity --journey-id ...`.

Safe recovery: run `synchronize_learning_journeys --journey-id ...`.

Escalate when source authority is missing or inconsistent.

## Operation stuck

Diagnostic action: run `reconcile_learning_journey_operations`.

Safe recovery: retry source capability only if its own service contract permits it.

Forbidden: mark an operation successful without source success.

## Authority revoked or missing

Diagnostic action: inspect source binding and institutional assignment.

Safe recovery: block governed actions and record integrity finding.

Forbidden: replace institutional authority with learner intent.

## Completion mismatch

Diagnostic action: evaluate institutional completion and inspect required competencies.

Safe recovery: rerun completion evaluation after progression is synchronized.

Forbidden: issue certificates, transcripts, or grades.

