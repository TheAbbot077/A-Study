# Governed Learning Journeys

PI-8B.1 introduces `learning_journeys` as a backend orchestration bounded context.

`LearningJourney` coordinates existing capabilities. It does not replace their domain authority.

The context owns:

- journey identity and type;
- top-level lifecycle;
- source binding;
- journey-level subject binding;
- capability references;
- current-step projection;
- available-action policy;
- deterministic blockers.

It does not own:

- self-study onboarding;
- curriculum resolution;
- diagnostics;
- bridge planning;
- teaching sessions;
- assessments;
- mastery;
- remediation;
- institutional membership.

Those records remain authoritative in their existing bounded contexts.

## Aggregate

`LearningJourney` records the learner, journey type, optional institution authority, lifecycle state, reason code, current step, timestamps, and optimistic version.

`LearningJourneySourceBinding` connects a journey to the workflow that established it. PI-8B.1 supports:

- `SELF_STUDY_WORKSPACE`;
- `INSTITUTION_MEMBERSHIP`.

`LearningJourneySubjectBinding` records durable subject authority at the journey level. It projects existing curriculum or institutional assignment authority into the journey context without replacing `CurriculumSubjectBinding`.

`LearningJourneyCapabilityReferences` stores read-safe identifiers for relevant capability records such as intent, diagnostic, bridge plan, teaching preparation, and active teaching session.

## Lifecycle

The lifecycle is explicit Python policy, not a generic database-configured workflow engine.

The initial lifecycle includes:

- `CREATED`
- `DISCOVERING_GOAL`
- `INTENT_CONFIRMED`
- `RESOLVING_CURRICULUM`
- `CURRICULUM_UNRESOLVED`
- `CURRICULUM_MATCHED`
- `SUBJECT_BINDING_REQUIRED`
- `SUBJECT_BINDING_UNAVAILABLE`
- `SUBJECT_BOUND`
- `STARTING_STATE_REQUIRED`
- `STARTING_STATE_IN_PROGRESS`
- `STARTING_STATE_CONFIRMED`
- `BRIDGE_REQUIRED`
- `PLAN_REQUIRED`
- `PLAN_READY`
- `LEARNING_ACTIVE`
- `LEARNING_BLOCKED`
- `PAUSED`
- `LEARNING_GOAL_COMPLETED`
- `WITHDRAWN`
- `ARCHIVED`

Terminal journeys do not silently return to active states.

## Frontend principle

Django determines workflow.

Clients render workflow.

Clients should consume journey read contracts instead of inferring the learner’s state from scattered statuses.
