# MVP Route Contract

This document captures the canonical PI-6B MVP route and API contract for manual and automated smoke testing.

## Frontend Routes

| User action | Frontend route | Auth | Status | Notes |
| --- | --- | --- | --- | --- |
| Open landing page | `/` | Public | Implemented | Entry point for the app shell |
| Open login page | `/login` | Public | Implemented | Accepts `next` redirect query |
| Open signup page | `/signup` | Public | Implemented | Accepts authenticated redirect guard |
| Open student dashboard | `/dashboard` | Authenticated | Implemented | Middleware redirect to `/login` when no session cookie exists |
| Open subject workspace | `/dashboard/subjects/:subjectId` | Authenticated | Implemented | Subject creation lands here |
| Open resource outline | `/dashboard/resources/:resourceId` | Authenticated | Implemented | Import status and concept browser |
| Open concept learning screen | `/dashboard/concepts/:conceptId` | Authenticated | Implemented | Supports `?session=` query |
| Open mastery check | `/dashboard/concepts/:conceptId/assessment` | Authenticated | Implemented | Results and remediation render in-page |
| Open dedicated remediation page | `/dashboard/remediation/:planId` | Authenticated | Intentionally deferred | No current frontend navigation target |
| Open dedicated progress page | `/dashboard/progress` | Authenticated | Intentionally deferred | Progress currently summarized inline only |

## Backend Endpoint Contract

| User action | Backend endpoint | Method | Auth | Status |
| --- | --- | --- | --- | --- |
| Register account | `/api/auth/register/` | `POST` | Public | Implemented |
| Log in | `/api/auth/login/` | `POST` | Public | Implemented |
| Log out | `/api/auth/logout/` | `POST` | Authenticated | Implemented |
| Resolve current user | `/api/auth/me/` | `GET` | Authenticated | Implemented |
| List subjects | `/api/academic/subjects/` | `GET` | Authenticated | Implemented |
| Create subject | `/api/academic/subjects/` | `POST` | Authenticated | Implemented |
| Get subject detail | `/api/academic/subjects/:subjectId/` | `GET` | Authenticated | Implemented |
| List learning resources by subject | `/api/academic/learning-resources/?subject=:subjectId` | `GET` | Authenticated | Implemented |
| Create learning resource | `/api/academic/learning-resources/` | `POST` | Authenticated | Implemented |
| Get resource detail | `/api/academic/learning-resources/:resourceId/` | `GET` | Authenticated | Implemented |
| List sections by resource | `/api/academic/content-sections/?learning_resource=:resourceId` | `GET` | Authenticated | Implemented |
| Get section detail | `/api/academic/content-sections/:sectionId/` | `GET` | Authenticated | Implemented |
| List concepts by resource | `/api/academic/content-concepts/?learning_resource=:resourceId` | `GET` | Authenticated | Implemented |
| Get concept detail | `/api/academic/content-concepts/:conceptId/` | `GET` | Authenticated | Implemented |
| Upload stored file | `/api/storage/files/` | `POST` | Authenticated | Implemented |
| List import jobs by resource | `/api/content-intelligence/import-jobs/?learning_resource=:resourceId` | `GET` | Authenticated | Implemented |
| Create import job | `/api/content-intelligence/import-jobs/` | `POST` | Authenticated | Implemented |
| Poll import job | `/api/content-intelligence/import-jobs/:importJobId/` | `GET` | Authenticated | Implemented |
| Retry import job | `/api/content-intelligence/import-jobs/:importJobId/retry/` | `POST` | Authenticated | Implemented |
| List concept browser state | `/api/learning/pedagogical-sessions/concept-browser/?learning_resource=:resourceId` | `GET` | Authenticated | Implemented |
| Start or resume concept | `/api/learning/pedagogical-sessions/start-or-resume/` | `POST` | Authenticated | Implemented |
| Get conversation state | `/api/learning/pedagogical-sessions/:sessionId/conversation/` | `GET` | Authenticated | Implemented |
| Generate teaching response | `/api/learning/pedagogical-sessions/:sessionId/teach/` | `POST` | Authenticated | Implemented |
| Ask Abbot question | `/api/learning/pedagogical-sessions/:sessionId/ask/` | `POST` | Authenticated | Implemented |
| Get mastery check snapshot | `/api/assessments/mastery-check/?content_concept=:conceptId` | `GET` | Authenticated | Implemented |
| Start mastery check | `/api/assessments/mastery-check/start/` | `POST` | Authenticated | Implemented |
| Submit assessment answer | `/api/assessments/mastery-check/:deliverySessionId/submit-answer/` | `POST` | Authenticated | Implemented |
| Complete mastery check | `/api/assessments/mastery-check/:deliverySessionId/complete/` | `POST` | Authenticated | Implemented |
| List remediation plans | `/api/remediation/plans/` | `GET` | Authenticated | Implemented |
| Create remediation plan | `/api/remediation/plans/` | `POST` | Authenticated | Implemented |
| Get remediation history | `/api/remediation/plans/history/` | `GET` | Authenticated | Implemented |
| Start remediation plan | `/api/remediation/plans/:planId/start/` | `POST` | Authenticated | Implemented |

## Current Deferred or Missing UI

| Concern | Status | Rationale |
| --- | --- | --- |
| Dedicated remediation page | Deferred | Current MVP renders remediation as a state inside the assessment flow |
| Dedicated progress dashboard | Deferred | Current MVP only exposes lightweight progress summaries inline |
| Dedicated import processing page | Deferred | Import status is rendered in the subject workspace rather than a standalone route |

## Manual Docker Commands

Frontend static audit:

```powershell
docker compose exec frontend npm run smoke:audit
```

Frontend browser smoke tests:

```powershell
docker compose exec frontend npx playwright install chromium
docker compose exec frontend npm run smoke:e2e
```

Full frontend smoke harness:

```powershell
docker compose exec frontend npm run smoke
```

Backend API smoke tests:

```powershell
docker compose exec backend pytest tests/test_mvp_smoke_api.py -q
```
