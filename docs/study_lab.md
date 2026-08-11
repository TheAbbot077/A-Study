# Study Lab

Study Lab is the learner-owned workspace layer for Abbot Study.

## Boundary

Study Lab composes authoritative systems by identifier only. It does not own curriculum, evidence, mastery, retrieval, teaching truth, or Ariel memory.

## Surface

- Workspaces
- Workspace context
- Resume state
- Panels and tools
- Tool availability and invocation
- Learner notes
- Workspace activity
- Snapshots

## Execution Model

PI-8C.4 uses synchronous application services for workspace assembly, availability, snapshots, and resume state. Background refresh remains a future optimization, not a current requirement.

## Interoperability

PI-8C.5 adds a governed tool registry, artefact metadata, lineage, manifests, and deterministic provider adapters. Provider integrations fail closed until authoritative bounded-context contracts are available.

## Execution Contract

The PI-8C.5 interoperability model is canonical.
The former invocation path is compatibility-only.
Legacy invocation events are historical and are not emitted by new commands.

Tool execution now converges on governed workspace tool sessions and canonical invocation lifecycle state. Legacy service entrypoints may remain as thin façades for backward compatibility, but they must delegate to the interoperability layer rather than dispatching providers directly.

Resume commands are idempotent by session, operation, and idempotency key.
Terminal session outcomes are orchestrated explicitly through canonical session services.

## Privacy

Learner notes, transcripts, and detailed activity remain private. Institutional projections are limited to governed, learner-safe facts.
