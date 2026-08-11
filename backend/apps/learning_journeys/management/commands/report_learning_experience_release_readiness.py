from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.learning_journeys.application.learning_experience_release_readiness import EvaluateLearningExperienceReleaseReadinessService


class Command(BaseCommand):
    help = "Report PI-8C.10 learning experience backend release readiness without claiming tests have passed."

    def add_arguments(self, parser):
        parser.add_argument("--fail-on-not-ready", action="store_true")

    def handle(self, *args, **options):
        report = EvaluateLearningExperienceReleaseReadinessService().report()
        self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        if options["fail_on_not_ready"] and report["result"] == "NOT_READY":
            raise CommandError("Learning experience release readiness is NOT_READY.")
