from __future__ import annotations

from django.db.models import Count

from ..domain.enums import LearningJourneyIntegrityFindingStatus, LearningJourneyOperationStatus, LearningJourneyStatus
from ..domain.models import LearningJourney, LearningJourneyActionReceipt, LearningJourneyIntegrityFinding, LearningJourneyOperation


class LearningJourneyOperationalMetricsService:
    def snapshot(self) -> dict:
        return {
            "journey_action_total": self._counts(LearningJourneyActionReceipt.objects.values("action_code", "status").annotate(count=Count("id")), ["action_code", "status"]),
            "journey_operation_total": self._counts(LearningJourneyOperation.objects.values("action_code", "status").annotate(count=Count("id")), ["action_code", "status"]),
            "journey_integrity_finding_total": self._counts(
                LearningJourneyIntegrityFinding.objects.values("code", "severity", "status").annotate(count=Count("id")),
                ["code", "severity", "status"],
            ),
            "journey_projection_stale_total": LearningJourney.objects.filter(last_synchronized_at__isnull=True).count(),
            "journey_operation_stuck_total": LearningJourneyOperation.objects.filter(
                status__in=[LearningJourneyOperationStatus.PENDING, LearningJourneyOperationStatus.RUNNING]
            ).count(),
            "journey_blocked_total": LearningJourney.objects.filter(status=LearningJourneyStatus.LEARNING_BLOCKED).count(),
            "journey_integrity_open_total": LearningJourneyIntegrityFinding.objects.filter(status=LearningJourneyIntegrityFindingStatus.OPEN).count(),
        }

    def _counts(self, rows, labels: list[str]) -> list[dict]:
        return [{label: row[label] for label in labels} | {"count": row["count"]} for row in rows]
