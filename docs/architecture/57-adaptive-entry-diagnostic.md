# PI-6F.4 Adaptive Entry Diagnostic

PI-6F.4 privately estimates a learner's defensible starting frontier inside one published PI-6F.3 graph. It does not grade, award mastery, modify curriculum, acquire materials, build a bridge path, or teach.

## Authority and privacy

A diagnostic freezes the active intent, immutable policy snapshot, published graph version and fingerprint, and published blueprint. The learner must acknowledge: **The diagnostic is used to personalize where learning begins.** Learner representations contain participation status, progress, the current prompt, neutral completion language, and permitted controls only. Answer keys, raw scores, correctness, confidence, estimates, rankings, academic levels, node classifications, thresholds, and internal profiles are server-private.

Diagnostic responses and estimates live exclusively in `self_study`; they are not assessment attempts, learning evidence, mastery profiles, formal grades, or transcript entries. Events contain identifiers and versions, never answers or internal estimates.

## Blueprint and item boundary

One immutable blueprint derives diagnosticable competencies, directly testable concepts, outcomes, entry candidates, external prerequisites, and domain groupings from a published graph. Physical, laboratory, oral, supervised, and explicitly unsupported nodes are recorded as not diagnosable. A blueprint publishes only when active validated items meet its minimum count and cover every diagnosticable node.

Items are curated or structured imports. Supported deterministic types are single choice, multiple choice, numeric, short structured, ordering, and matching. There is no production inference or free-form LLM judge. Changing a scoring rule requires a new item version.

## Delivery, scoring, and adaptation

There is at most one outstanding presentation. Refresh returns it; learners cannot choose hidden item identifiers. Accepted responses are immutable and protected by a diagnostic-scoped idempotency key and canonical payload hash. Exact replay succeeds; conflicting replay fails. Schema validation and scoring occur server-side.

The versioned rules engine prioritizes untested/high-uncertainty nodes, graph importance, appropriate difficulty, and stable item identity while excluding prior presentations. One answer remains tentative. At least two consistent observations are required for demonstrated or not-demonstrated classification, avoiding lucky-answer and single-error propagation.

## Placement and controls

Finalization distinguishes demonstrated, not demonstrated, unobserved, uncertain, and not diagnosable. A starting frontier requires governed estimate and confidence thresholds and cannot depend on a required prerequisite identified as a gap. Insufficient items, unstable frontier, or excessive uncertainty produces an immutable inconclusive profile.

Profiles fingerprint the diagnostic, graph, blueprint, item and response identities/hashes, scoring version, estimates, thresholds, frontier, gaps, and uncertainty. Challenges do not mutate profiles. Checkpoints use the same governed diagnostic boundary. Retakes create a new diagnostic; a prior profile is superseded only after a successful replacement profile.
