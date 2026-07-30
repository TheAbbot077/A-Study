from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.learning_journeys.application.operational import LearningJourneyIntegrityService
from apps.learning_journeys.domain.models import LearningJourney


class Command(BaseCommand):
    help = "Check learning journey operational integrity and record durable findings."

    def add_arguments(self, parser):
        parser.add_argument("--journey-id", dest="journey_id")
        parser.add_argument("--tenant-id", dest="tenant_id")
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--repair", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--actor-email", dest="actor_email")

    def handle(self, *args, **options):
        queryset = LearningJourney.objects.select_related("learner").order_by("updated_at")
        if options["journey_id"]:
            queryset = queryset.filter(id=options["journey_id"])
        if options.get("tenant_id"):
            queryset = queryset.filter(institution_id=options["tenant_id"])
        actor = self._actor(options.get("actor_email"))
        processed = findings = failed = 0
        for journey in queryset[: options["limit"]]:
            processed += 1
            if options["dry_run"]:
                self.stdout.write(f"dry-run integrity journey={journey.id} status={journey.status}")
                continue
            try:
                result = LearningJourneyIntegrityService().check(journey_id=journey.id, actor=actor or journey.learner, repair=options["repair"])
                findings += len(result["findings"])
            except Exception as exc:  # pragma: no cover - operator feedback path
                failed += 1
                self.stderr.write(f"failed journey={journey.id} code={type(exc).__name__}")
        self.stdout.write(f"processed={processed} findings={findings} failed={failed} repair={options['repair']} dry_run={options['dry_run']}")

    def _actor(self, email: str | None):
        if not email:
            return None
        return get_user_model().objects.get(email=email)
