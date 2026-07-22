# PI-6F.9 — Self-Study Onboarding and Subject Workspace

PI-6F.9 adds the learner-facing doorway into the governed self-study pipeline.

The workspace is a learner-owned product container. Learners may call it a
subject, but its `display_name` is not an Academic `Subject` and cannot create
or mutate curriculum, graph, diagnostic, bridge-plan, teaching-preparation, or
teaching-session authority.

## Boundaries

- Curriculum graph remains the authority for what must be learned.
- Diagnostic placement remains private and is not serialized as mastery.
- Evidence mapping and coverage remain governed material authorities.
- Bridge plans and teaching preparations remain downstream governed artifacts.
- The workspace reads and links to those artifacts; it does not replace them.

## Backend

`SelfStudyWorkspace` stores learner, tenant, display metadata, lifecycle status,
and optional references to existing PI-6F authorities.

`SelfStudyWorkspaceMaterial` associates existing `LearningResource` and
`ContentProcessingJob` records with a workspace. It does not duplicate files or
create a new upload pipeline.

`SelfStudyOnboardingService` computes the backend-authoritative next action:

- complete intent;
- upload materials;
- wait for processing;
- resolve material issues;
- start or resume diagnostic;
- wait for mapping, bridge planning, or teaching preparation;
- start or resume learning;
- contact support for blocked/stale/archived states.

The next-action response contains stable blocker codes and safe identifiers
only. It does not expose raw diagnostic responses, private placement estimates,
source text, unsafe material details, or internal processing traces.

## API surface

Routes live under `/api/self-study/workspaces/` and follow the existing DRF
problem/permission conventions.

The workspace API supports create/list/retrieve/update/archive, onboarding and
next-action projections, intent attachment/creation/update, material
association/status, diagnostic status/start, and learning status.

## Frontend

The frontend doorway is `/dashboard/self-study`.

It provides:

- workspace dashboard and creation flow;
- workspace overview;
- next-action card;
- intent/material/diagnostic/plan/learn section routes;
- material status and blocker rendering;
- diagnostic start/resume CTA when allowed by backend state.

The frontend renders backend state. It does not infer curriculum, mastery,
diagnostic placement, or teaching readiness.

## Manual validation

Run the standard Docker validation commands from the repository root. Do not
interpret this document as a claim that validation has passed.
