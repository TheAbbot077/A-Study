# Self-study journey orchestration

PI-8B.2 adds a journey orchestration layer over the existing self-study bounded context.

The orchestration rule is:

```text
LearningJourney coordinates workflow.
Self-study services remain authoritative for domain decisions.
```

The orchestrator loads a `LearningJourney`, verifies it is a self-study journey, resolves the bound `SelfStudyWorkspace`, checks the shared action policy, delegates to the source capability, synchronizes the journey projection, writes a durable action receipt, and returns the read-safe journey contract.

It does not create curriculum authority, diagnostic results, bridge plans, learning plans, teaching content, mastery, or remediation decisions.

## Transaction boundaries

Journey receipts and lifecycle records are local to `learning_journeys`. Source capability services own their own transaction semantics. After a successful source command, the orchestrator synchronizes the journey from source state rather than returning speculative state.

If synchronization fails after a source command succeeds, the source record remains authoritative and the command can be retried or synchronized safely.

## Existing API compatibility

Existing self-study APIs remain capability APIs. The journey API is the workflow coordination surface.

```text
journey API     = what should happen next in the learning journey
capability API  = detailed domain interaction for onboarding, diagnostics, planning, teaching
```
