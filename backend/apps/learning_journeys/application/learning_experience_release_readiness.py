from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from apps.core.events.registry import default_event_registry


REQUIRED_LEARNING_EXPERIENCE_EVENTS = [
    "learning_journey.created",
    "learning_journey.progressed",
    "study_lab.artefact.created",
    "study_lab.scaffold_generation.completed",
    "ariel.knowledge.created",
]


@dataclass(frozen=True)
class LearningExperienceReleaseReadinessResult:
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


class EvaluateLearningExperienceReleaseReadinessService:
    stale_after = timedelta(hours=24)

    def report(self, *, run_integrity_scan: bool = False, batch_size: int = 100) -> dict:
        blockers: list[dict] = []
        warnings: list[dict] = []
        self._event_registration(blockers=blockers)
        self._integrity(blockers=blockers, warnings=warnings)
        self._projection_health(warnings=warnings)
        self._provider_degradation(warnings=warnings)
        self._policy_state(blockers=blockers)
        self._known_limitations(warnings=warnings)
        result = "READY"
        if blockers:
            result = "NOT_READY"
        elif warnings:
            result = "READY_WITH_WARNINGS"
        return LearningExperienceReleaseReadinessResult(
            result=result,
            blockers=blockers,
            warnings=warnings,
            summary=self._summary(),
        ).to_dict()

    def _event_registration(self, *, blockers: list[dict]) -> None:
        missing = [event for event in REQUIRED_LEARNING_EXPERIENCE_EVENTS if event not in default_event_registry._subscribers]
        if missing:
            blockers.append({"code": "REQUIRED_EVENTS_NOT_REGISTERED", "message": "Required learning experience events are not registered.", "details": {"events": missing}})

    def _integrity(self, *, blockers: list[dict], warnings: list[dict]) -> None:
        try:
            from apps.learning_journeys.domain.models import LearningJourneyIntegrityFinding, LearningJourneyIntegrityFindingStatus, LearningJourneyIntegritySeverity
        except Exception as exc:
            blockers.append({"code": "LEARNING_JOURNEY_INTEGRITY_UNAVAILABLE", "message": "Learning journey integrity models unavailable.", "details": {"error": type(exc).__name__}})
            return
        critical = LearningJourneyIntegrityFinding.objects.filter(
            status=LearningJourneyIntegrityFindingStatus.OPEN,
            severity__in=[LearningJourneyIntegritySeverity.CRITICAL, LearningJourneyIntegritySeverity.BLOCKING],
        ).count()
        if critical:
            blockers.append({"code": "OPEN_CRITICAL_INTEGRITY_FINDINGS", "message": "Open critical or blocking integrity findings exist.", "details": {"count": critical}})
        noncritical = LearningJourneyIntegrityFinding.objects.filter(status=LearningJourneyIntegrityFindingStatus.OPEN).exclude(
            severity__in=[LearningJourneyIntegritySeverity.CRITICAL, LearningJourneyIntegritySeverity.BLOCKING]
        ).count()
        if noncritical:
            warnings.append({"code": "OPEN_NONCRITICAL_INTEGRITY_FINDINGS", "message": "Open non-critical integrity findings exist.", "details": {"count": noncritical}})

    def _projection_health(self, *, warnings: list[dict]) -> None:
        try:
            from apps.learning_journeys.domain.models import LearningJourney
        except Exception:
            return
        cutoff = timezone.now() - self.stale_after
        stale = LearningJourney.objects.filter(last_synchronized_at__isnull=True).count() + LearningJourney.objects.filter(last_synchronized_at__lt=cutoff).count()
        if stale:
            warnings.append({"code": "STALE_JOURNEY_PROJECTIONS", "message": "Some learning journey projections are stale or unsynchronized.", "details": {"count": stale}})

    def _provider_degradation(self, *, warnings: list[dict]) -> None:
        provider_checks = {
            "study_lab.scaffold_generation": "Study Lab scaffold generation is intentionally fail-closed until configured.",
            "ariel.provider": "Ariel production provider availability may be intentionally limited in this environment.",
        }
        for code, detail in provider_checks.items():
            warnings.append({"code": "OPTIONAL_PROVIDER_UNAVAILABLE", "message": detail, "details": {"provider": code}})

    def _policy_state(self, *, blockers: list[dict]) -> None:
        if "apps.learning_journeys" not in apps.app_configs:
            blockers.append({"code": "LEARNING_JOURNEY_APP_MISSING", "message": "Learning journeys app is not installed.", "details": {}})

    def _known_limitations(self, *, warnings: list[dict]) -> None:
        warnings.append({"code": "KNOWN_LIMITATION", "message": "Institutional classroom roster authority remains deferred and explicit participant authority is used instead.", "details": {"classification": "FUTURE_CAPABILITY"}})

    def _summary(self) -> dict:
        return {
            "installed_apps_checked": sorted(apps.app_configs.keys()),
            "registered_event_count": len(default_event_registry._subscribers),
            "required_event_count": len(REQUIRED_LEARNING_EXPERIENCE_EVENTS),
        }
