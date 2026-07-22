# 64. Diagnostic and Study-Plan Experience

PI-6F.10 adds the learner-facing diagnostic and study-plan experience for self-study workspaces.

The package is intentionally an experience/read-projection layer. It does not create a new diagnostic algorithm, curriculum graph, bridge planner, teaching-preparation authority, teaching session framework, or mastery authority.

## Authority boundaries

- PI-6F.4 remains the authority for entry diagnostic session state, private placement, and diagnostic privacy.
- PI-6F.5 remains the authority for coverage and material blockers.
- PI-6F.6 remains the authority for the bridge plan, plan nodes, findings, activation, staleness, and ordering.
- PI-6F.7 remains the authority for teaching preparation and retrieval readiness.
- PI-6F.8 remains the authority for learner-facing teaching sessions.
- PI-6F.9 remains the learner-owned workspace shell and next-action doorway.

The frontend may call the active bridge plan “your study plan”, but backend services continue to read the governed bridge plan and do not mutate plan computation.

## Diagnostic experience

Workspace diagnostic endpoints expose:

- a start/resume experience projection;
- a safe progress summary;
- diagnostic start/resume delegation into PI-6F.4;
- a learner-safe placement summary after governed diagnostic completion.

The summary deliberately excludes raw answers, item-level scores, adaptive routing internals, private estimates, and comparative rankings. Learner copy states that diagnostic placement is not mastery, credit, or a grade.

## Study-plan experience

Workspace plan endpoints expose:

- plan summary and currentness blockers;
- ordered learner-readable plan nodes;
- safe finding summaries;
- learning launch eligibility.

Learning launch fails closed unless the plan is active and current, required material blockers are absent, teaching preparation is ready, and an existing teaching session is available through PI-6F.8.

## Frontend experience

The self-study diagnostic route shows:

- diagnostic intro and privacy reminders;
- start/resume controls;
- progress and blocked states;
- summary link after completion.

The diagnostic summary route shows learner-safe placement bands and domains, with explicit “not mastery” copy.

The study-plan route shows:

- governed study-plan status;
- required/optional/blocked counts;
- ordered nodes;
- PI-6F.5 coverage meanings;
- findings and blockers;
- a start-learning CTA only when backend readiness permits it.

## Validation

Manual Docker validation should include backend checks, migration drift checks, targeted PI-6F.10 backend tests, frontend typecheck/lint, route-contract tests, route audit, and smoke tests. This document does not claim those checks have passed.
