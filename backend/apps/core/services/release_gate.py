from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.apps import apps
from django.conf import settings
from django.utils import timezone

from apps.core.domain.models import BusinessEventDelivery, BusinessEventDeliveryStatus
from apps.core.events.registry import default_event_registry
@dataclass(frozen=True)
class BackendReleaseGateResult:
    result: str
    blockers: list[dict]
    warnings: list[dict]
    summary: dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "result": self.result,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "summary": self.summary,
        }


class EvaluateBackendReleaseGateService:
    stale_after = timedelta(hours=24)
    stuck_processing_after = timedelta(hours=2)

    def report(self) -> dict:
        blockers: list[dict] = []
        warnings: list[dict] = []

        from apps.learning_journeys.application.learning_experience_release_readiness import EvaluateLearningExperienceReleaseReadinessService
        from apps.learning_journeys.application.release_readiness import LearningJourneyReleaseReadinessService

        learning_journey = LearningJourneyReleaseReadinessService().report()
        learning_experience = EvaluateLearningExperienceReleaseReadinessService().report()

        self._configuration(blockers=blockers, warnings=warnings)
        self._app_installation(blockers=blockers)
        self._event_platform(blockers=blockers, warnings=warnings)
        self._dependency_summary(warnings=warnings)
        self._runtime_posture(warnings=warnings)
        self._release_gate_thresholds(learning_journey=learning_journey, learning_experience=learning_experience, blockers=blockers, warnings=warnings)

        if learning_journey["result"] == "NOT_READY":
            blockers.append({"code": "LEARNING_JOURNEY_NOT_READY", "message": "Learning journey release readiness is not ready.", "details": learning_journey})
        elif learning_journey["result"] == "READY_WITH_WARNINGS":
            warnings.append({"code": "LEARNING_JOURNEY_WARNINGS", "message": "Learning journey release readiness has warnings.", "details": learning_journey})

        if learning_experience["result"] == "NOT_READY":
            blockers.append({"code": "LEARNING_EXPERIENCE_NOT_READY", "message": "Learning experience release readiness is not ready.", "details": learning_experience})
        elif learning_experience["result"] == "READY_WITH_WARNINGS":
            warnings.append({"code": "LEARNING_EXPERIENCE_WARNINGS", "message": "Learning experience release readiness has warnings.", "details": learning_experience})

        result = "READY"
        if blockers:
            result = "NOT_READY"
        elif warnings:
            result = "READY_WITH_WARNINGS"
        return BackendReleaseGateResult(result=result, blockers=blockers, warnings=warnings, summary=self._summary(learning_journey, learning_experience)).to_dict()

    def _configuration(self, *, blockers: list[dict], warnings: list[dict]) -> None:
        secret_key = getattr(settings, "SECRET_KEY", "")
        if not secret_key or secret_key in {"unsafe-local-dev-key", "replace-me-later"}:
            warnings.append({"code": "CRITICAL_CONFIGURATION_INVALID", "message": "Production-safe SECRET_KEY is not configured for the current environment.", "details": {"setting": "DJANGO_SECRET_KEY"}})
        if not getattr(settings, "ALLOWED_HOSTS", []):
            warnings.append({"code": "ALLOWED_HOSTS_NOT_SET", "message": "Allowed hosts configuration is empty.", "details": {}})

    def _app_installation(self, *, blockers: list[dict]) -> None:
        required_apps = ["core", "learning_journeys", "study_lab", "assessments", "content_processing", "storage"]
        missing = [app_label for app_label in required_apps if app_label not in apps.app_configs]
        if missing:
            blockers.append({"code": "REQUIRED_APPS_MISSING", "message": "Required backend apps are not installed.", "details": {"apps": missing}})

    def _event_platform(self, *, blockers: list[dict], warnings: list[dict]) -> None:
        pending = BusinessEventDelivery.objects.filter(status=BusinessEventDeliveryStatus.PENDING).count()
        retryable = BusinessEventDelivery.objects.filter(status=BusinessEventDeliveryStatus.FAILED_RETRYABLE).count()
        terminal = BusinessEventDelivery.objects.filter(status=BusinessEventDeliveryStatus.FAILED_TERMINAL).count()
        stuck = BusinessEventDelivery.objects.filter(
            status=BusinessEventDeliveryStatus.PROCESSING,
            processing_started_at__lt=timezone.now() - self.stuck_processing_after,
        ).count()
        if terminal:
            blockers.append({"code": "EVENT_TERMINAL_FAILURES_PRESENT", "message": "Terminal durable-event failures are present.", "details": {"count": terminal}})
        if pending or retryable:
            warnings.append({"code": "EVENT_BACKLOG_WARNING", "message": "Durable event backlog is present.", "details": {"pending": pending, "retryable": retryable}})
        if stuck:
            warnings.append({"code": "EVENT_BACKLOG_CRITICAL", "message": "Some durable events are stuck in processing.", "details": {"count": stuck}})
        if "learning.conversation_initialized" not in default_event_registry._subscribers:
            warnings.append({"code": "EVENT_REGISTRY_INCOMPLETE", "message": "Not all runtime event registrations are present in this environment.", "details": {"event": "learning.conversation_initialized"}})

    def _dependency_summary(self, *, warnings: list[dict]) -> None:
        warnings.append({"code": "DEPENDENCY_SUMMARY", "message": "Operational dependency posture should be validated per deployment environment.", "details": {"database": "critical", "redis": "async_or_degraded", "celery": "operationally_visible"}})

    def _runtime_posture(self, *, warnings: list[dict]) -> None:
        if getattr(settings, "DEBUG", False):
            warnings.append({"code": "DEBUG_MODE_ENABLED", "message": "Debug mode is enabled.", "details": {}})

    def _release_gate_thresholds(self, *, learning_journey: dict, learning_experience: dict, blockers: list[dict], warnings: list[dict]) -> None:
        if learning_journey["result"] == "NOT_READY" or learning_experience["result"] == "NOT_READY":
            blockers.append({"code": "RELEASE_GATE_BLOCKED", "message": "One or more domain release-readiness services reported NOT_READY.", "details": {"learning_journey": learning_journey["result"], "learning_experience": learning_experience["result"]}})
        elif learning_journey["result"] == "READY_WITH_WARNINGS" or learning_experience["result"] == "READY_WITH_WARNINGS":
            warnings.append({"code": "RELEASE_GATE_DEGRADED", "message": "One or more domain release-readiness services reported warnings.", "details": {"learning_journey": learning_journey["result"], "learning_experience": learning_experience["result"]}})

    def _summary(self, learning_journey: dict, learning_experience: dict) -> dict:
        return {
            "installed_apps": sorted(apps.app_configs.keys()),
            "registered_event_count": len(default_event_registry._subscribers),
            "learning_journey_result": learning_journey["result"],
            "learning_experience_result": learning_experience["result"],
            "stale_after_hours": int(self.stale_after.total_seconds() // 3600),
        }
