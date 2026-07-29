from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.assessments.domain.models import LearningEvidence, MasteryDecision
from apps.core.events import BusinessEvent, EventPublisher
from apps.self_study.graph_models import CurriculumEdge, CurriculumNode, EdgeType, RequirementType
from apps.users.domain.models import User

from ..domain.enums import (
    LearningCompetencyProgressReason,
    LearningCompetencyProgressState,
    LearningCompetencyUnlockState,
)
from ..domain.models import LearningCompetencyProgress, LearningCompetencyProgressHistory, LearningJourney
from .progression_policy import CompetencyProgressionPolicy
from .services import SynchronizeLearningJourneyService, can_read_journey


def _event(events: EventPublisher, name: str, payload: dict):
    events.publish(BusinessEvent.create(name, payload=payload))


DEMONSTRATED_STATES = {
    LearningCompetencyProgressState.DEMONSTRATED,
    LearningCompetencyProgressState.REINFORCED,
}


@dataclass(frozen=True)
class CompetencyProgressSnapshot:
    journey_id: str
    completed_competencies: list[dict]
    active_competencies: list[dict]
    emerging_competencies: list[dict]
    review_competencies: list[dict]
    locked_competencies: list[dict]
    next_available_competencies: list[dict]

    def to_dict(self) -> dict:
        return {
            "journey_id": self.journey_id,
            "completed_competencies": self.completed_competencies,
            "active_competencies": self.active_competencies,
            "emerging_competencies": self.emerging_competencies,
            "review_competencies": self.review_competencies,
            "locked_competencies": self.locked_competencies,
            "next_available_competencies": self.next_available_competencies,
        }


class CompetencyUnlockPolicy:
    def newly_available_after(self, *, journey: LearningJourney, competency: CurriculumNode) -> list[CurriculumNode]:
        downstream = CurriculumEdge.objects.select_related("source_node").filter(
            graph_version=competency.graph_version,
            edge_type=EdgeType.REQUIRES,
            requirement=RequirementType.REQUIRED,
            target_node=competency,
        )
        available = []
        demonstrated_ids = set(
            LearningCompetencyProgress.objects.filter(journey=journey, state__in=DEMONSTRATED_STATES).values_list("competency_id", flat=True)
        )
        for edge in downstream:
            candidate = edge.source_node
            required_prerequisites = CurriculumEdge.objects.filter(
                graph_version=candidate.graph_version,
                edge_type=EdgeType.REQUIRES,
                requirement=RequirementType.REQUIRED,
                source_node=candidate,
            ).values_list("target_node_id", flat=True)
            if set(required_prerequisites) <= demonstrated_ids:
                available.append(candidate)
        return available


class CompetencyProgressionService:
    def __init__(
        self,
        *,
        events: EventPublisher | None = None,
        policy: CompetencyProgressionPolicy | None = None,
        unlock_policy: CompetencyUnlockPolicy | None = None,
    ):
        self.events = events or EventPublisher()
        self.policy = policy or CompetencyProgressionPolicy()
        self.unlock_policy = unlock_policy or CompetencyUnlockPolicy()

    @transaction.atomic
    def progress_from_mastery(self, *, journey_id, competency_id, mastery_decision_id, actor: User | None = None) -> LearningCompetencyProgress:
        journey = LearningJourney.objects.select_for_update().get(id=journey_id)
        if actor and not can_read_journey(actor, journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        competency = CurriculumNode.objects.get(id=competency_id)
        mastery = MasteryDecision.objects.get(id=mastery_decision_id, learner=journey.learner)
        progress, created = LearningCompetencyProgress.objects.select_for_update().get_or_create(
            journey=journey,
            competency=competency,
            defaults={
                "state": LearningCompetencyProgressState.NOT_STARTED,
                "unlock_state": LearningCompetencyUnlockState.AVAILABLE,
            },
        )
        old_state = progress.state
        old_unlock = progress.unlock_state
        decision = self.policy.decide(current_state=progress.state, current_unlock_state=progress.unlock_state, mastery_decision=mastery)
        evidence_summary = self._evidence_summary(mastery)
        changed = progress.transition_to(
            decision.state,
            unlock_state=decision.unlock_state,
            mastery_decision=mastery,
            evidence_summary=evidence_summary,
        )
        if not changed and not created:
            return progress
        progress.save()
        self._history(
            progress=progress,
            old_state=old_state,
            new_state=progress.state,
            old_unlock=old_unlock,
            new_unlock=progress.unlock_state,
            reason=decision.reason if decision.changed else LearningCompetencyProgressReason.INITIALIZED,
            mastery=mastery,
            actor=actor,
            metadata={"created": created},
        )
        self._publish_progress_event(progress)
        unlocked = self.unlock_downstream(journey=journey, competency=competency, actor=actor)
        JourneyEvolutionService(events=self.events).evolve_after_progress(progress=progress, unlocked=unlocked, actor=actor)
        return progress

    @transaction.atomic
    def supersede_competency(self, *, journey_id, competency_id, successor_competency_id=None, actor: User | None = None) -> LearningCompetencyProgress:
        journey = LearningJourney.objects.select_for_update().get(id=journey_id)
        if actor and not can_read_journey(actor, journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        progress = LearningCompetencyProgress.objects.select_for_update().get(journey=journey, competency_id=competency_id)
        old_state = progress.state
        old_unlock = progress.unlock_state
        decision = self.policy.supersede(current_state=progress.state, current_unlock_state=progress.unlock_state)
        successor = CurriculumNode.objects.get(id=successor_competency_id) if successor_competency_id else None
        changed = progress.transition_to(decision.state, unlock_state=decision.unlock_state)
        if successor:
            progress.superseded_by = successor
            changed = True
        if changed:
            progress.save()
            self._history(
                progress=progress,
                old_state=old_state,
                new_state=progress.state,
                old_unlock=old_unlock,
                new_unlock=progress.unlock_state,
                reason=decision.reason,
                actor=actor,
                metadata={"successor_competency_id": str(successor.id) if successor else ""},
            )
            self._publish_progress_event(progress)
        return progress

    def unlock_downstream(self, *, journey: LearningJourney, competency: CurriculumNode, actor: User | None = None) -> list[LearningCompetencyProgress]:
        unlocked = []
        for node in self.unlock_policy.newly_available_after(journey=journey, competency=competency):
            progress, created = LearningCompetencyProgress.objects.get_or_create(
                journey=journey,
                competency=node,
                defaults={
                    "state": LearningCompetencyProgressState.NOT_STARTED,
                    "unlock_state": LearningCompetencyUnlockState.AVAILABLE,
                },
            )
            if created:
                self._history(
                    progress=progress,
                    old_state=LearningCompetencyProgressState.NOT_STARTED,
                    new_state=progress.state,
                    old_unlock=LearningCompetencyUnlockState.LOCKED,
                    new_unlock=progress.unlock_state,
                    reason=LearningCompetencyProgressReason.INITIALIZED,
                    actor=actor,
                    metadata={"unlock_source": str(competency.id)},
                )
            elif progress.unlock_state == LearningCompetencyUnlockState.LOCKED:
                old_unlock = progress.unlock_state
                progress.transition_to(progress.state, unlock_state=LearningCompetencyUnlockState.AVAILABLE)
                progress.save()
                self._history(
                    progress=progress,
                    old_state=progress.state,
                    new_state=progress.state,
                    old_unlock=old_unlock,
                    new_unlock=progress.unlock_state,
                    reason=LearningCompetencyProgressReason.MASTERY_DEMONSTRATED,
                    actor=actor,
                    metadata={"unlock_source": str(competency.id)},
                )
            unlocked.append(progress)
        return unlocked

    def _evidence_summary(self, mastery: MasteryDecision) -> dict:
        evidence_ids = mastery.metadata.get("evidence_ids", []) if isinstance(mastery.metadata, dict) else []
        latest = LearningEvidence.objects.filter(id__in=evidence_ids).order_by("-created_at").first() if evidence_ids else None
        return {
            "mastery_decision_id": str(mastery.id),
            "decision": mastery.decision,
            "confidence": mastery.confidence,
            "evidence_count": mastery.evidence_count,
            "latest_evidence_id": str(latest.id) if latest else "",
            "latest_evidence_type": latest.evidence_type if latest else "",
        }

    def _history(self, *, progress, old_state, new_state, old_unlock, new_unlock, reason, mastery=None, actor=None, metadata=None):
        evidence_id = ""
        if mastery and isinstance(mastery.metadata, dict):
            evidence_ids = mastery.metadata.get("evidence_ids") or []
            evidence_id = evidence_ids[0] if evidence_ids else ""
        LearningCompetencyProgressHistory.objects.create(
            progress=progress,
            journey=progress.journey,
            competency=progress.competency,
            old_state=old_state,
            new_state=new_state,
            old_unlock_state=old_unlock,
            new_unlock_state=new_unlock,
            reason=reason,
            triggering_evidence_id=evidence_id or None,
            triggering_mastery_decision=mastery,
            actor=actor,
            metadata=metadata or {},
        )

    def _publish_progress_event(self, progress: LearningCompetencyProgress):
        event_name = {
            LearningCompetencyProgressState.EMERGING: "learning_competency.emerging",
            LearningCompetencyProgressState.DEVELOPING: "learning_competency.emerging",
            LearningCompetencyProgressState.DEMONSTRATED: "learning_competency.demonstrated",
            LearningCompetencyProgressState.REINFORCED: "learning_competency.reinforced",
            LearningCompetencyProgressState.REVIEW_REQUIRED: "learning_competency.review_required",
            LearningCompetencyProgressState.REGRESSED: "learning_competency.regressed",
            LearningCompetencyProgressState.SUPERSEDED: "learning_competency.superseded",
        }.get(progress.state)
        if not event_name:
            return
        transaction.on_commit(
            lambda: _event(
                self.events,
                event_name,
                {
                    "journey_id": str(progress.journey_id),
                    "competency_id": str(progress.competency_id),
                    "progress_id": str(progress.id),
                    "state": progress.state,
                    "unlock_state": progress.unlock_state,
                    "mastery_decision_id": str(progress.latest_mastery_decision_id or ""),
                },
            )
        )


class JourneyEvolutionService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    def evolve_after_progress(self, *, progress: LearningCompetencyProgress, unlocked: list[LearningCompetencyProgress], actor: User | None = None) -> LearningJourney:
        if progress.journey.source_bindings.exists():
            journey = SynchronizeLearningJourneyService(events=self.events).execute(journey_id=progress.journey_id, actor=actor or progress.journey.learner)
        else:
            journey = progress.journey
        transaction.on_commit(
            lambda: _event(
                self.events,
                "journey.evolved",
                {
                    "journey_id": str(journey.id),
                    "triggering_competency_id": str(progress.competency_id),
                    "state": journey.status,
                    "unlocked_competency_ids": [str(item.competency_id) for item in unlocked],
                },
            )
        )
        LearningPlanEvolutionService(events=self.events).request_evolution(journey=journey, triggering_progress=progress, unlocked=unlocked)
        return journey


class LearningPlanEvolutionService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    def request_evolution(self, *, journey: LearningJourney, triggering_progress: LearningCompetencyProgress, unlocked: list[LearningCompetencyProgress]) -> dict:
        payload = {
            "journey_id": str(journey.id),
            "triggering_competency_id": str(triggering_progress.competency_id),
            "newly_unlocked_competency_ids": [str(item.competency_id) for item in unlocked],
            "reason": "COMPETENCY_PROGRESSION",
        }
        transaction.on_commit(lambda: _event(self.events, "learning_plan.evolution_requested", payload))
        return payload


class CompetencyProgressSnapshotService:
    def execute(self, *, journey_id, actor: User) -> dict:
        journey = LearningJourney.objects.get(id=journey_id)
        if not can_read_journey(actor, journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        rows = list(
            LearningCompetencyProgress.objects.select_related("competency", "latest_mastery_decision")
            .filter(journey=journey)
            .order_by("competency__ordinal", "competency__stable_key")
        )
        snapshot = CompetencyProgressSnapshot(
            journey_id=str(journey.id),
            completed_competencies=[self._row(row) for row in rows if row.state in DEMONSTRATED_STATES],
            active_competencies=[self._row(row) for row in rows if row.unlock_state == LearningCompetencyUnlockState.ACTIVE],
            emerging_competencies=[
                self._row(row)
                for row in rows
                if row.state in {LearningCompetencyProgressState.EMERGING, LearningCompetencyProgressState.DEVELOPING}
            ],
            review_competencies=[self._row(row) for row in rows if row.state == LearningCompetencyProgressState.REVIEW_REQUIRED],
            locked_competencies=[self._row(row) for row in rows if row.unlock_state == LearningCompetencyUnlockState.LOCKED],
            next_available_competencies=[self._row(row) for row in rows if row.unlock_state == LearningCompetencyUnlockState.AVAILABLE],
        )
        return snapshot.to_dict()

    def journey_progress(self, *, journey_id, actor: User) -> dict:
        snapshot = self.execute(journey_id=journey_id, actor=actor)
        return {
            "journey_id": snapshot["journey_id"],
            "current_learning_phase": self._phase(snapshot),
            "active_competency": (snapshot["active_competencies"] or snapshot["next_available_competencies"] or [None])[0],
            "next_competency": (snapshot["next_available_competencies"] or [None])[0],
            "blocked_competencies": snapshot["review_competencies"],
            "available_competencies": snapshot["next_available_competencies"],
            "completed_competency_count": len(snapshot["completed_competencies"]),
        }

    def _phase(self, snapshot: dict) -> str:
        if snapshot["review_competencies"]:
            return "REVIEW"
        if snapshot["active_competencies"] or snapshot["next_available_competencies"]:
            return "LEARNING"
        if snapshot["completed_competencies"]:
            return "PROGRESSING"
        return "NOT_STARTED"

    def _row(self, row: LearningCompetencyProgress) -> dict:
        return {
            "progress_id": str(row.id),
            "competency_id": str(row.competency_id),
            "stable_key": row.competency.stable_key,
            "title": row.competency.title,
            "node_type": row.competency.node_type,
            "state": row.state,
            "unlock_state": row.unlock_state,
            "latest_mastery_decision_id": str(row.latest_mastery_decision_id or ""),
            "latest_mastery_decision": row.latest_mastery_decision.decision if row.latest_mastery_decision_id else "",
            "evidence_count": row.latest_evidence_summary.get("evidence_count", 0),
            "last_progressed_at": row.last_progressed_at.isoformat() if row.last_progressed_at else None,
        }
