from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.learning_journeys.domain.enums import LearningJourneyOperationStatus
from apps.learning_journeys.domain.models import LearningJourneyOperation


class Command(BaseCommand):
    help = "Report orphaned or long-running learning journey operations without mutating learning policy state."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        queryset = LearningJourneyOperation.objects.select_related("journey", "receipt").filter(
            status__in=[LearningJourneyOperationStatus.PENDING, LearningJourneyOperationStatus.RUNNING]
        )[: options["limit"]]
        processed = orphaned = 0
        for operation in queryset:
            processed += 1
            if not operation.receipt_id:
                orphaned += 1
            self.stdout.write(
                f"operation={operation.id} journey={operation.journey_id} action={operation.action_code} status={operation.status} orphaned={not operation.receipt_id}"
            )
        self.stdout.write(f"processed={processed} orphaned={orphaned} dry_run={options['dry_run']}")
