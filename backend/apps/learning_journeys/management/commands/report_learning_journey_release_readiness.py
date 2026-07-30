from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.learning_journeys.application.release_readiness import LearningJourneyReleaseReadinessService


class Command(BaseCommand):
    help = "Report PI-8B learning journey backend release readiness without claiming tests have passed."

    def add_arguments(self, parser):
        parser.add_argument("--run-integrity-scan", action="store_true")
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--fail-on-not-ready", action="store_true")

    def handle(self, *args, **options):
        report = LearningJourneyReleaseReadinessService().report(
            run_integrity_scan=options["run_integrity_scan"],
            batch_size=options["batch_size"],
        )
        self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        if options["fail_on_not_ready"] and report["result"] == "NOT_READY":
            raise CommandError("Learning journey release readiness is NOT_READY.")
