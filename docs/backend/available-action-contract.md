# Available Action Contract

Learning journeys expose backend-defined available actions.

Each action contains:

- `code`;
- `label`;
- `method`;
- `endpoint_name`;
- `enabled`;
- `disabled_reason`;
- `requires_confirmation`.

Initial action codes include:

- `BEGIN_GOAL_DISCOVERY`
- `CONTINUE_GOAL_DISCOVERY`
- `CONFIRM_INTENT`
- `RETRY_CURRICULUM_RESOLUTION`
- `SELECT_CURRICULUM`
- `BEGIN_DIAGNOSTIC`
- `CONTINUE_DIAGNOSTIC`
- `GENERATE_BRIDGE_PLAN`
- `GENERATE_LEARNING_PLAN`
- `ACTIVATE_LEARNING_PLAN`
- `BEGIN_TEACHING_SESSION`
- `CONTINUE_TEACHING_SESSION`
- `RETRY_BLOCKED_STEP`
- `PAUSE_JOURNEY`
- `RESUME_JOURNEY`
- `WITHDRAW_JOURNEY`
- `SYNCHRONIZE`

PI-8B.1 does not implement every domain command behind these actions. It establishes the read contract and safe lifecycle commands.

Self-study intent, diagnostic, curriculum selection, and teaching commands remain in their authoritative bounded contexts until explicit adapter commands are added.
