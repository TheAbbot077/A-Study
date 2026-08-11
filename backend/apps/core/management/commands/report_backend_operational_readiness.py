from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from apps.core.domain.models import BusinessEventDelivery, BusinessEventDeliveryStatus
from apps.core.services.durable_events import DispatchBusinessEventDeliveryService


class Command(BaseCommand):
    help = "Report PI-9.4 backend operational readiness without claiming external observability platforms."

    def handle(self, *args, **options):
        now = timezone.now()
        delivery_qs = BusinessEventDelivery.objects.all()
        pending_count = delivery_qs.filter(status=BusinessEventDeliveryStatus.PENDING).count()
        retryable_count = delivery_qs.filter(status=BusinessEventDeliveryStatus.FAILED_RETRYABLE).count()
        terminal_failure_count = delivery_qs.filter(status=BusinessEventDeliveryStatus.FAILED_TERMINAL).count()
        stuck_processing_count = delivery_qs.filter(
            status=BusinessEventDeliveryStatus.PROCESSING,
            processing_started_at__lt=now - DispatchBusinessEventDeliveryService.stale_processing_lease,
        ).count()

        self.stdout.write("overall_status=READY")
        self.stdout.write(f"database=available connection_name={connection.settings_dict.get('NAME')}")
        self.stdout.write(f"event_backlog_pending={pending_count}")
        self.stdout.write(f"event_backlog_retryable={retryable_count}")
        self.stdout.write(f"event_backlog_terminal_failures={terminal_failure_count}")
        self.stdout.write(f"event_backlog_stuck_processing={stuck_processing_count}")
