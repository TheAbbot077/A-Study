# PI-7A — Conversational Onboarding and Governed Curriculum Discovery

PI-7A replaces the temporary learner-facing raw subject identifier with a conversational onboarding journey for self-study workspaces.

The capability lets a learner describe what they want to study, why they are studying it, and any exam or curriculum context they know. The system then presents governed curriculum candidates from the existing curriculum registry. Learner text is discovery input only; it never creates a curriculum, subject, syllabus, qualification, or graph.

## Architecture

The implementation adds a workspace-scoped `SelfStudyOnboarding` aggregate inside the existing `self_study` bounded context.

The aggregate records:

- learner and tenant scope;
- workspace;
- lifecycle status and current stage;
- topic and study intent;
- qualification, jurisdiction, awarding-body, and level context;
- target date and weekly study availability;
- active durable curriculum resolution attempt;
- selected resolver-produced candidate and learner-safe candidate snapshot;
- created intent once complete;
- version and lifecycle timestamps.

Django model discovery follows the existing self-study pattern: the concrete model lives in `onboarding_models.py` and is imported by `models.py`.

## Lifecycle

Supported statuses:

- `DRAFT`
- `COLLECTING_CONTEXT`
- `RESOLVING_CURRICULUM`
- `AWAITING_CURRICULUM_SELECTION`
- `REVIEWING_SUMMARY`
- `COMPLETED`
- `STALE`
- `ABANDONED`

The backend determines the current stage. The frontend renders the stage; it does not manufacture onboarding completion.

## Curriculum discovery

PI-7A reuses the existing PI-6F.2 curriculum resolver as the candidate authority. The discovery step creates a durable onboarding-scoped `CurriculumResolutionAttempt`, runs the normal resolver evaluation path, and projects resolver-produced `CurriculumResolutionCandidate` rows into learner-safe candidate cards.

Candidate projections include title, subject, authority, qualification, jurisdiction, level, version label, rank, and a safe match explanation. Hidden scoring internals are not exposed.

If no candidate matches, the learner is asked to refine the topic or context. Abbot does not fabricate a syllabus.

Candidate ordering comes from the resolver. The frontend submits only a resolver `candidate_id` for selection; it cannot authorize an arbitrary curriculum version.

## Governed subject binding

`SelfStudyIntent` still requires explicit Academic `Subject` authority. PI-7A therefore adds `CurriculumSubjectBinding`, a small registry-to-subject binding model owned by the self-study bounded context.

Onboarding completion can use a subject only when the selected resolver candidate has an active binding for the learner tenant. PI-7A does not create Academic subjects from learner text or registry labels. A verified curriculum without a binding is shown as unavailable for self-study with the stable blocker `CURRICULUM_SUBJECT_BINDING_MISSING`.

## Intent integration

Completion creates a normal `SelfStudyIntent` using existing intent services and the selected candidate's governed subject binding, marks it ready, activates it through the existing policy snapshot service, and starts the existing intent-scoped curriculum resolution flow with the selected curriculum version as the requested version.

## Frontend

The route `/dashboard/self-study/:workspaceId/intent` now renders `ConversationalOnboarding`.

The UI is conversational but deterministic:

- Abbot prompt cards;
- learner answer fields;
- governed intent choices;
- curriculum candidate cards;
- summary;
- backend-authorized next action.

The ordinary learner journey no longer asks for a raw governed subject ID.

## Events

Registered event names:

- `self_study.onboarding.started`
- `self_study.onboarding.context_updated`
- `self_study.onboarding.curriculum_resolution_requested`
- `self_study.onboarding.curriculum_candidates_available`
- `self_study.onboarding.curriculum_selected`
- `self_study.onboarding.completed`
- `self_study.onboarding.abandoned`
- `self_study.onboarding.marked_stale`

Payloads remain identifier-focused and avoid raw diagnostic data.

## Manual validation

Do not claim validation until Docker checks are run manually.

Recommended commands:

```powershell
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py test apps.self_study.tests.test_conversational_onboarding
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
docker compose exec frontend npm run smoke:audit
docker compose exec frontend npx playwright test tests/smoke/self-study-onboarding.spec.ts --project=chromium
docker compose exec frontend npm run smoke:e2e
```
