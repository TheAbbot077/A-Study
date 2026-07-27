# PI-7B.4–PI-7B.7 — Learning Identity Memory, Preferences, Review, and Timeline

This slice completes the governed Learning Identity foundation.

It adds:

- neutral observed learning identity records;
- source synchronization receipts;
- learner correction and contestation records;
- governed learner preferences;
- learner-safe memory/timeline read models;
- a purpose-limited mentor-context contract;
- the first learner-facing “What Abbot remembers” surface.

Learning Identity still does not own curricula, diagnostics, teaching, assessment scoring, mastery, transcripts, credentials, or progression decisions.

## Observation boundary

Observed identity records are neutral event memories. They can say that a learner completed a diagnostic or a governed learning session. They cannot say the learner mastered a concept, is weak at a subject, has a learning style, or has a medical/accessibility condition.

Observation synchronization uses a controlled source envelope. Source-domain ORM objects and raw payloads do not cross into the Learning Identity domain.

Currently wired source adapters are intentionally narrow:

- self-study completed entry diagnostics;
- self-study completed teaching sessions.

Future concept-check, Ariel, and exam-simulation events must be added through the same controlled registry once those authoritative source records exist.

## Review and correction

Learners may withdraw learner-owned declarations by creating a successor profile version. Published history is preserved.

Learners may contest observations. Contesting does not rewrite source-domain history; it records a correction request and removes the contested observation from mentor-context eligibility.

Verified or future derived attributes require governed review rather than direct learner overwrite.

## Preferences

Preferences are learner-controlled settings, not facts about the learner.

The initial preference registry supports:

- explanation mode;
- teaching pace;
- interface language;
- session length;
- reduced motion;
- high contrast;
- larger text;
- captions.

Accessibility/display preferences are functional choices. They are not diagnoses or inferred learner traits.

## Timeline and mentor context

Timeline entries are learner-safe projections assembled from authoritative lifecycle records. They are ordered deterministically and avoid raw audit details.

Mentor context is a compact structured contract assembled for a declared purpose. It excludes mastery claims, hidden scores, raw transcripts, rejected/superseded facts, resolver rankings, diagnostic estimates, and contested observations.

## API surface

The API is mounted under:

`/api/learning-identity/profiles/`

Key routes:

- `GET /api/learning-identity/profiles/`
- `GET /api/learning-identity/profiles/{profile_id}/`
- `GET /api/learning-identity/profiles/{profile_id}/timeline/`
- `GET /api/learning-identity/profiles/{profile_id}/mentor-context/?purpose=...`
- `POST /api/learning-identity/profiles/{profile_id}/preferences/`
- `POST /api/learning-identity/profiles/{profile_id}/preferences/withdraw/`
- `POST /api/learning-identity/profiles/{profile_id}/declarations/{attribute_id}/withdraw/`
- `POST /api/learning-identity/profiles/{profile_id}/observations/{observation_id}/contest/`

The learner-facing frontend route is:

`/dashboard/self-study/memory`

It displays “What Abbot remembers”, recent eligible learning activity, study preferences, and the learner-safe journey timeline.

## Manual validation

The coding agent did not run validation. Recommended manual commands:

```powershell
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend pytest apps/learning_identity
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run lint
docker compose exec frontend npm run smoke:audit
docker compose exec frontend npx playwright test tests/smoke/learning-identity-memory.spec.ts --project=chromium
docker compose exec frontend npm run smoke:e2e
```
