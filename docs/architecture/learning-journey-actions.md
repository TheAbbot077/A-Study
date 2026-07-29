# Learning journey actions

Journey actions are explicitly registered in `SelfStudyJourneyActionPolicy`.

The registry defines:

- action code;
- allowed journey statuses;
- source capability;
- whether the action is executable through the journey orchestrator;
- confirmation requirements;
- disabled reason when an action is intentionally not executable yet.

The API never dispatches arbitrary user input to Python methods. Unregistered actions are rejected and recorded as action receipts.

## Implemented self-study actions

- `BEGIN_GOAL_DISCOVERY`
- `CONTINUE_GOAL_DISCOVERY`
- `CONFIRM_INTENT`
- `RESOLVE_CURRICULUM`
- `RETRY_CURRICULUM_RESOLUTION`
- `SELECT_CURRICULUM`
- `BEGIN_DIAGNOSTIC`
- `CONTINUE_DIAGNOSTIC`
- `CONFIRM_PLACEMENT`
- `RETRY_BLOCKED_STEP`
- `PAUSE_JOURNEY`
- `RESUME_JOURNEY`
- `WITHDRAW_JOURNEY`
- `SYNCHRONIZE`

## Registered but disabled actions

These actions are visible as known workflow concepts but are not executed by the journey orchestrator until the source bounded context exposes a safe command contract:

- `REVISE_INTENT`
- `GENERATE_BRIDGE_PLAN`
- `GENERATE_LEARNING_PLAN`
- `ACTIVATE_LEARNING_PLAN`
- `PREPARE_TEACHING_SESSION`
- `BEGIN_TEACHING_SESSION`
- `CONTINUE_TEACHING_SESSION`

Disabled actions fail closed with a receipt and learner-safe reason.
