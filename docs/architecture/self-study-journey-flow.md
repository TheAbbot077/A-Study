# Self-Study Journey Flow

PI-8B.1 maps existing self-study authority into a shared journey projection.

The self-study source remains `SelfStudyWorkspace`. The journey adapter reads:

- workspace;
- onboarding;
- intent;
- curriculum resolution;
- curriculum subject binding;
- diagnostic;
- bridge plan;
- teaching preparation;
- active teaching session.

The adapter is read-only. It does not mutate self-study records.

## Initial mappings

| Source condition | Journey state | Current step |
| --- | --- | --- |
| Workspace exists, no confirmed intent | `DISCOVERING_GOAL` | `DISCOVER_GOAL` |
| Intent confirmed, resolution pending | `RESOLVING_CURRICULUM` | `RESOLVE_CURRICULUM` |
| No governed curriculum | `CURRICULUM_UNRESOLVED` | `RESOLVE_CURRICULUM` |
| Candidate selection required | `CURRICULUM_MATCHED` | `SELECT_CURRICULUM` |
| Verified curriculum lacks self-study binding | `SUBJECT_BINDING_UNAVAILABLE` | `WAIT_FOR_SUBJECT_BINDING` |
| Subject bound, no diagnostic | `STARTING_STATE_REQUIRED` | `COMPLETE_ENTRY_DIAGNOSTIC` |
| Diagnostic active | `STARTING_STATE_IN_PROGRESS` | `COMPLETE_ENTRY_DIAGNOSTIC` |
| Placement exists, no plan | `PLAN_REQUIRED` | `CREATE_LEARNING_PLAN` |
| Bridge plan not active | `BRIDGE_REQUIRED` | `COMPLETE_BRIDGE` |
| Plan exists, teaching not prepared | `PLAN_READY` | `BEGIN_LEARNING` |
| Teaching content blocked | `LEARNING_BLOCKED` | `RESOLVE_BLOCKER` |
| Teaching ready | `LEARNING_ACTIVE` | `BEGIN_LEARNING` or `CONTINUE_LEARNING` |

The journey projection may mention blocker codes, but learner-facing copy should be produced by product clients from safe titles and descriptions.
