from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.apps import apps
from django.db.models import Count
from django.utils import timezone

from apps.core.events.registry import default_event_registry

from ..domain.enums import (
    LearningJourneyIntegrityFindingStatus,
    LearningJourneyIntegritySeverity,
    LearningJourneyOperationStatus,
    LearningJourneySourceType,
    LearningJourneyType,
)
from ..domain.models import (
    InstitutionalLearningAssignment,
    LearningJourney,
    LearningJourneyIntegrityFinding,
    LearningJourneyOperation,
    LearningJourneySourceBinding,
    LearningJourneySubjectBinding,
)
from .operational import LearningJourneyIntegrityService


REQUIRED_JOURNEY_EVENTS = [
    "learning_journey.created",
    "learning_journey.synchronized",
    "learning_journey.state_changed",
    "learning_journey.action_accepted",
    "learning_journey.action_succeeded",
    "learning_journey.action_failed",
    "learning_journey.action_rejected",
    "learning_journey.command_conflicted",
    "learning_journey.operation_started",
    "learning_journey.operation_completed",
    "learning_journey.operation_failed",
    "learning_journey.integrity_finding_detected",
    "learning_journey.integrity_finding_resolved",
    "journey.evolved",
    "learning_plan.evolution_requested",
    "institutional_journey.assigned",
    "institutional_journey.accepted",
    "institutional_journey.activated",
    "institutional_completion.ready",
    "institutional_completion.completed",
]

REQUIRED_SELF_STUDY_TASKS = [
    "self_study.resolve_curriculum",
    "self_study.create_bridge_plan",
    "self_study.finalize_bridge_plan",
    "self_study.assemble_teaching_preparation",
    "self_study.evaluate_teaching_readiness",
    "self_study.prepare_teaching_turn",
    "self_study.record_teaching_evidence",
    "self_study.advance_teaching_session",
]


@dataclass(frozen=True)
class ReleaseReadinessResult:
    result: str
    blockers: list[dict]
    warnings: list[dict]
    summary: dict

    def to_dict(self) -> dict:
        return {
            "result": self.result,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "summary": self.summary,
        }


class LearningJourneyReleaseReadinessService:
    stale_after = timedelta(hours=24)
    stuck_after = timedelta(hours=2)

    def report(self, *, run_integrity_scan: bool = False, batch_size: int = 100) -> dict:
        blockers: list[dict] = []
        warnings: list[dict] = []
        if run_integrity_scan:
            self._scan_sample(batch_size=batch_size)
        self._event_registration(blockers=blockers)
        self._task_registration(blockers=blockers, warnings=warnings)
        self._critical_findings(blockers=blockers, warnings=warnings)
        self._stale_projections(warnings=warnings)
        self._stuck_operations(blockers=blockers, warnings=warnings)
        self._authority_conflicts(blockers=blockers)
        result = "READY"
        if blockers:
            result = "NOT_READY"
        elif warnings:
            result = "READY_WITH_WARNINGS"
        return ReleaseReadinessResult(
            result=result,
            blockers=blockers,
            warnings=warnings,
            summary=self._summary(),
        ).to_dict()

    def _scan_sample(self, *, batch_size: int) -> None:
        service = LearningJourneyIntegrityService()
        for journey in LearningJourney.objects.select_related("learner").order_by("updated_at")[:batch_size]:
            service.check(journey_id=journey.id, actor=journey.learner)

    def _event_registration(self, *, blockers: list[dict]) -> None:
        missing = [event for event in REQUIRED_JOURNEY_EVENTS if event not in default_event_registry._subscribers]
        if missing:
            blockers.append({"code": "REQUIRED_EVENTS_NOT_REGISTERED", "message": "Required learning journey events are not registered.", "details": {"events": missing}})

    def _task_registration(self, *, blockers: list[dict], warnings: list[dict]) -> None:
        try:
            from apps.self_study.infrastructure.celery import tasks as self_study_tasks
        except Exception as exc:  # pragma: no cover - defensive import reporting
            blockers.append({"code": "SELF_STUDY_TASKS_NOT_IMPORTABLE", "message": "Self-study task module could not be imported.", "details": {"error": type(exc).__name__}})
            return
        registered = {getattr(value, "name", "") for value in vars(self_study_tasks).values()}
        missing = [task for task in REQUIRED_SELF_STUDY_TASKS if task not in registered]
        if missing:
            warnings.append({"code": "REQUIRED_TASKS_NOT_REGISTERED", "message": "Some journey-adjacent self-study tasks are not registered.", "details": {"tasks": missing}})

    def _critical_findings(self, *, blockers: list[dict], warnings: list[dict]) -> None:
        critical = LearningJourneyIntegrityFinding.objects.filter(
            status=LearningJourneyIntegrityFindingStatus.OPEN,
            severity__in=[LearningJourneyIntegritySeverity.CRITICAL, LearningJourneyIntegritySeverity.BLOCKING],
        ).count()
        noncritical = LearningJourneyIntegrityFinding.objects.filter(status=LearningJourneyIntegrityFindingStatus.OPEN).exclude(
            severity__in=[LearningJourneyIntegritySeverity.CRITICAL, LearningJourneyIntegritySeverity.BLOCKING]
        ).count()
        if critical:
            blockers.append({"code": "OPEN_CRITICAL_INTEGRITY_FINDINGS", "message": "Open critical or blocking integrity findings exist.", "details": {"count": critical}})
        if noncritical:
            warnings.append({"code": "OPEN_NONCRITICAL_INTEGRITY_FINDINGS", "message": "Open non-critical integrity findings exist.", "details": {"count": noncritical}})

    def _stale_projections(self, *, warnings: list[dict]) -> None:
        cutoff = timezone.now() - self.stale_after
        stale = LearningJourney.objects.filter(last_synchronized_at__isnull=True).count() + LearningJourney.objects.filter(last_synchronized_at__lt=cutoff).count()
        if stale:
            warnings.append({"code": "STALE_PROJECTIONS", "message": "Some journey projections are stale or unsynchronized.", "details": {"count": stale}})

    def _stuck_operations(self, *, blockers: list[dict], warnings: list[dict]) -> None:
        cutoff = timezone.now() - self.stuck_after
        stuck = LearningJourneyOperation.objects.filter(
            status__in=[LearningJourneyOperationStatus.PENDING, LearningJourneyOperationStatus.RUNNING],
            started_at__lt=cutoff,
        ).count()
        if stuck:
            blockers.append({"code": "STUCK_OPERATIONS", "message": "Learning journey operations are stuck beyond policy threshold.", "details": {"count": stuck}})
        active = LearningJourneyOperation.objects.filter(status__in=[LearningJourneyOperationStatus.PENDING, LearningJourneyOperationStatus.RUNNING]).count()
        if active and not stuck:
            warnings.append({"code": "ACTIVE_OPERATIONS", "message": "Learning journey operations are currently active.", "details": {"count": active}})

    def _authority_conflicts(self, *, blockers: list[dict]) -> None:
        institutional_without_assignment = LearningJourney.objects.filter(journey_type=LearningJourneyType.INSTITUTIONAL).exclude(
            id__in=InstitutionalLearningAssignment.objects.values("journey_id")
        ).count()
        self_study_with_institutional_source = LearningJourney.objects.filter(
            journey_type=LearningJourneyType.SELF_STUDY,
            source_bindings__source_type=LearningJourneySourceType.INSTITUTIONAL_ASSIGNMENT,
        ).count()
        if institutional_without_assignment:
            blockers.append(
                {
                    "code": "INSTITUTIONAL_AUTHORITY_MISSING",
                    "message": "Institutional journeys without assignment authority exist.",
                    "details": {"count": institutional_without_assignment},
                }
            )
        if self_study_with_institutional_source:
            blockers.append(
                {
                    "code": "SELF_STUDY_AUTHORITY_CONFLICT",
                    "message": "Self-study journeys with institutional source authority exist.",
                    "details": {"count": self_study_with_institutional_source},
                }
            )

    def _summary(self) -> dict:
        by_type = list(LearningJourney.objects.values("journey_type").annotate(count=Count("id")).order_by("journey_type"))
        by_status = list(LearningJourney.objects.values("status").annotate(count=Count("id")).order_by("status"))
        return {
            "journey_count": LearningJourney.objects.count(),
            "journey_counts_by_type": {item["journey_type"]: item["count"] for item in by_type},
            "journey_counts_by_status": {item["status"]: item["count"] for item in by_status},
            "source_binding_count": LearningJourneySourceBinding.objects.count(),
            "subject_binding_count": LearningJourneySubjectBinding.objects.count(),
            "operation_count": LearningJourneyOperation.objects.count(),
            "open_integrity_finding_count": LearningJourneyIntegrityFinding.objects.filter(status=LearningJourneyIntegrityFindingStatus.OPEN).count(),
            "legacy_self_study_workspaces_without_journey": self._legacy_workspace_backfill_count(),
            "installed_apps_checked": sorted(apps.app_configs.keys()),
        }

    def _legacy_workspace_backfill_count(self) -> int:
        try:
            from apps.self_study.workspace_models import SelfStudyWorkspace
        except Exception:
            return 0
        bound_workspace_ids = LearningJourneySourceBinding.objects.filter(source_type=LearningJourneySourceType.SELF_STUDY_WORKSPACE).values_list("source_id", flat=True)
        return SelfStudyWorkspace.objects.exclude(id__in=bound_workspace_ids).count()
