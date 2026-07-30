# PI-8B Backend Validation Manifest

Run from the repository root:

```powershell
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend pytest apps/learning_journeys
docker compose exec backend pytest apps/self_study
docker compose exec backend pytest apps/learning_identity
docker compose exec backend pytest apps/academic
docker compose exec backend pytest apps/academic_review
docker compose exec backend pytest apps/assessments
docker compose exec backend pytest apps/assessment_review
docker compose exec backend pytest apps/content_processing
docker compose exec backend pytest apps/content_intelligence
docker compose exec backend pytest apps/retrieval
docker compose exec backend pytest apps/remediation
docker compose exec backend pytest apps/users
docker compose exec backend pytest apps/audit
docker compose exec backend pytest apps/notifications
docker compose exec backend pytest apps/core
docker compose exec backend pytest
```

No `apps/mastery` test path currently exists in the repository; mastery decisions are represented under `apps/assessments`.

