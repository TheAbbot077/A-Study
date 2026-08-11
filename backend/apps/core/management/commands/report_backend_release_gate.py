from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.core.services.release_gate import EvaluateBackendReleaseGateService


class Command(BaseCommand):
    help = "Report PI-9.5 backend enterprise release gate readiness without claiming a freeze verdict."

    def add_arguments(self, parser):
        parser.add_argument("--fail-on-not-ready", action="store_true")

    def handle(self, *args, **options):
        report = EvaluateBackendReleaseGateService().report()
        self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        if options["fail_on_not_ready"] and report["result"] == "NOT_READY":
            raise CommandError("Backend enterprise release gate is NOT_READY.")
