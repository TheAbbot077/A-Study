from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.learning_journeys.application.backfill import LearningJourneyBackfillService


class Command(BaseCommand):
    help = "Backfill missing learning journeys from legacy source records with bounded, tenant-safe dry-run support."

    def add_arguments(self, parser):
        parser.add_argument("--source", choices=["self-study-workspaces"], default="self-study-workspaces")
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--tenant-id", dest="tenant_id")
        parser.add_argument("--actor-email", dest="actor_email", required=True)
        parser.add_argument("--execute", action="store_true", help="Actually create missing journeys. Omit for dry-run.")

    def handle(self, *args, **options):
        actor = get_user_model().objects.get(email=options["actor_email"])
        if options["source"] != "self-study-workspaces":
            raise CommandError("Unsupported backfill source.")
        result = LearningJourneyBackfillService().backfill_self_study_workspaces(
            actor=actor,
            limit=options["limit"],
            dry_run=not options["execute"],
            tenant_id=options.get("tenant_id"),
        )
        self.stdout.write(
            "processed={processed} created={created} unchanged={unchanged} failed={failed} dry_run={dry_run}".format(**result)
        )
        for failure in result["failures"]:
            self.stderr.write(f"failed source={failure['source_type']} id={failure['source_id']} code={failure['code']}")
        if result["failed"]:
            raise CommandError("Backfill completed with failures.")

