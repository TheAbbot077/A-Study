from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import InstitutionMembership, InstitutionRole, User

from ..domain.enums import (
    InstitutionalAssignmentState,
    InstitutionalCompletionState,
    InstitutionalInterventionReason,
    InstitutionalInterventionSeverity,
    InstitutionalInterventionStatus,
    LearningCompetencyProgressState,
    LearningJourneyType,
)
from ..domain.models import (
    InstitutionalInterventionRecommendation,
    InstitutionalLearningAssignment,
    LearningCompetencyProgress,
    LearningJourney,
)
from .authority import INSTITUTION_STAFF_ROLES, InstitutionAuthorityProvider, JourneyAuthorityResolver
from .progression_services import DEMONSTRATED_STATES
from .services import SynchronizeLearningJourneyService


def _event(events: EventPublisher, name: str, payload: dict):
    events.publish(BusinessEvent.create(name, payload=payload))


class InstitutionalJourneyVisibilityPolicy:
    institution_visible_fields = {
        "journey_state",
        "assigned_competencies",
        "progress_summary",
        "required_interventions",
        "completion_readiness",
    }

    learner_private_fields = {
        "private_notes",
        "reflection_drafts",
        "mentor_memory",
        "learning_identity_private_context",
    }

    def can_view_assignment(self, *, actor: User, assignment: InstitutionalLearningAssignment) -> bool:
        if actor.is_superuser or actor.id == assignment.learner_id:
            return True
        return InstitutionMembership.objects.filter(
            user=actor,
            institution=assignment.institution,
            is_active=True,
            role__in=INSTITUTION_STAFF_ROLES,
        ).exists()

    def filter_institutional_payload(self, payload: dict) -> dict:
        return {key: value for key, value in payload.items() if key not in self.learner_private_fields}


class InstitutionalAcceptancePolicy:
    def can_activate(self, *, assignment: InstitutionalLearningAssignment, actor: User) -> bool:
        if assignment.acceptance_mode == "AUTO_ACCEPT":
            return True
        if assignment.acceptance_mode == "LEARNER_CONFIRMATION_REQUIRED":
            return actor.id == assignment.learner_id
        if assignment.acceptance_mode == "ADMIN_CONFIRMATION_REQUIRED":
            return InstitutionAuthorityProvider().can_complete(actor=actor, journey=assignment.journey)
        return False


@dataclass(frozen=True)
class InstitutionalCompletionDecision:
    ready: bool
    completed_required_competency_ids: list[str]
    missing_required_competency_ids: list[str]
    blockers: list[str]


class InstitutionalCompletionPolicy:
    def evaluate(self, *, assignment: InstitutionalLearningAssignment) -> InstitutionalCompletionDecision:
        required_ids = [str(item) for item in assignment.required_competency_ids]
        completed_ids = set(
            str(item)
            for item in LearningCompetencyProgress.objects.filter(
                journey=assignment.journey,
                state__in=DEMONSTRATED_STATES,
            ).values_list("competency_id", flat=True)
        )
        missing = [competency_id for competency_id in required_ids if competency_id not in completed_ids]
        blockers = []
        if missing:
            blockers.append("REQUIRED_COMPETENCIES_INCOMPLETE")
        return InstitutionalCompletionDecision(
            ready=not missing,
            completed_required_competency_ids=[competency_id for competency_id in required_ids if competency_id in completed_ids],
            missing_required_competency_ids=missing,
            blockers=blockers,
        )


class InstitutionalCompletionService:
    def __init__(self, *, events: EventPublisher | None = None, policy: InstitutionalCompletionPolicy | None = None):
        self.events = events or EventPublisher()
        self.policy = policy or InstitutionalCompletionPolicy()

    @transaction.atomic
    def evaluate(self, *, journey_id, actor: User) -> dict:
        journey = LearningJourney.objects.select_for_update().get(id=journey_id, journey_type=LearningJourneyType.INSTITUTIONAL)
        JourneyAuthorityResolver().require_can_read(actor=actor, journey=journey)
        assignment = InstitutionalLearningAssignment.objects.select_for_update().get(journey=journey)
        decision = self.policy.evaluate(assignment=assignment)
        if decision.ready and assignment.mark_completion_ready():
            assignment.save()
            transaction.on_commit(
                lambda: _event(
                    self.events,
                    "institutional_completion.ready",
                    {"journey_id": str(journey.id), "assignment_id": str(assignment.id), "institution_id": str(assignment.institution_id)},
                )
            )
        elif not decision.ready and assignment.completion_state != InstitutionalCompletionState.PENDING:
            assignment.completion_state = InstitutionalCompletionState.BLOCKED
            assignment.version += 1
            assignment.save(update_fields=["completion_state", "version", "updated_at"])
        return self._payload(assignment=assignment, decision=decision)

    @transaction.atomic
    def complete(self, *, journey_id, actor: User) -> dict:
        journey = LearningJourney.objects.select_for_update().get(id=journey_id, journey_type=LearningJourneyType.INSTITUTIONAL)
        provider = JourneyAuthorityResolver().provider_for(journey=journey)
        if not provider.can_complete(actor=actor, journey=journey):
            raise PermissionDenied("INSTITUTIONAL_COMPLETION_PERMISSION_DENIED")
        assignment = InstitutionalLearningAssignment.objects.select_for_update().get(journey=journey)
        decision = self.policy.evaluate(assignment=assignment)
        if not decision.ready:
            raise ValidationError("Institutional completion requirements are not satisfied.", code="INSTITUTIONAL_COMPLETION_NOT_READY")
        changed = assignment.mark_completed()
        assignment.save()
        if changed:
            transaction.on_commit(
                lambda: _event(
                    self.events,
                    "institutional_completion.completed",
                    {"journey_id": str(journey.id), "assignment_id": str(assignment.id), "institution_id": str(assignment.institution_id)},
                )
            )
        SynchronizeLearningJourneyService(events=self.events).execute(journey_id=journey.id, actor=actor)
        return self._payload(assignment=assignment, decision=decision)

    def _payload(self, *, assignment: InstitutionalLearningAssignment, decision: InstitutionalCompletionDecision) -> dict:
        return {
            "journey_id": str(assignment.journey_id),
            "assignment_id": str(assignment.id),
            "completion_state": assignment.completion_state,
            "ready": decision.ready,
            "completed_required_competency_ids": decision.completed_required_competency_ids,
            "missing_required_competency_ids": decision.missing_required_competency_ids,
            "blockers": decision.blockers,
        }


class InstitutionalInterventionService:
    def __init__(self, *, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def evaluate_for_progress(self, *, progress: LearningCompetencyProgress, actor: User | None = None) -> InstitutionalInterventionRecommendation | None:
        journey = progress.journey
        if journey.journey_type != LearningJourneyType.INSTITUTIONAL:
            return None
        assignment = InstitutionalLearningAssignment.objects.select_for_update().get(journey=journey)
        reason = ""
        severity = InstitutionalInterventionSeverity.MEDIUM
        action = ""
        if progress.state == LearningCompetencyProgressState.REVIEW_REQUIRED:
            reason = InstitutionalInterventionReason.REPEATED_REVIEW_REQUIRED
            action = "Review this competency with the learner and recommend targeted support."
        elif progress.state == LearningCompetencyProgressState.REGRESSED:
            reason = InstitutionalInterventionReason.PERSISTENT_REGRESSION
            severity = InstitutionalInterventionSeverity.HIGH
            action = "Arrange instructor support before the learner continues this required competency."
        if not reason:
            return None
        existing = InstitutionalInterventionRecommendation.objects.filter(
            assignment=assignment,
            triggering_progress=progress,
            reason=reason,
            status__in={InstitutionalInterventionStatus.OPEN, InstitutionalInterventionStatus.ACKNOWLEDGED, InstitutionalInterventionStatus.IN_PROGRESS},
        ).first()
        if existing:
            return existing
        recommendation = InstitutionalInterventionRecommendation.objects.create(
            journey=journey,
            assignment=assignment,
            institution=assignment.institution,
            learner=assignment.learner,
            triggering_progress=progress,
            reason=reason,
            severity=severity,
            recommended_action=action,
        )
        assignment.assignment_state = InstitutionalAssignmentState.INTERVENTION_REQUIRED
        assignment.version += 1
        assignment.save(update_fields=["assignment_state", "version", "updated_at"])
        transaction.on_commit(
            lambda: _event(
                self.events,
                "institutional_intervention.created",
                {
                    "journey_id": str(journey.id),
                    "assignment_id": str(assignment.id),
                    "intervention_id": str(recommendation.id),
                    "reason": reason,
                },
            )
        )
        return recommendation

    @transaction.atomic
    def resolve(self, *, recommendation_id, actor: User, status: str = InstitutionalInterventionStatus.RESOLVED) -> InstitutionalInterventionRecommendation:
        recommendation = InstitutionalInterventionRecommendation.objects.select_for_update().select_related("assignment", "journey").get(id=recommendation_id)
        if not InstitutionAuthorityProvider().can_complete(actor=actor, journey=recommendation.journey):
            raise PermissionDenied("INSTITUTIONAL_INTERVENTION_PERMISSION_DENIED")
        changed = recommendation.resolve(actor=actor, status=status)
        if changed:
            recommendation.save()
            if not recommendation.assignment.interventions.filter(
                status__in={InstitutionalInterventionStatus.OPEN, InstitutionalInterventionStatus.ACKNOWLEDGED, InstitutionalInterventionStatus.IN_PROGRESS}
            ).exists():
                recommendation.assignment.assignment_state = InstitutionalAssignmentState.ACTIVE
                recommendation.assignment.version += 1
                recommendation.assignment.save(update_fields=["assignment_state", "version", "updated_at"])
            transaction.on_commit(
                lambda: _event(
                    self.events,
                    "institutional_intervention.resolved",
                    {
                        "journey_id": str(recommendation.journey_id),
                        "assignment_id": str(recommendation.assignment_id),
                        "intervention_id": str(recommendation.id),
                        "status": recommendation.status,
                    },
                )
            )
        return recommendation


class InstitutionalLearningPlanEvolutionService:
    def request_projection(self, *, assignment: InstitutionalLearningAssignment) -> dict:
        return {
            "journey_id": str(assignment.journey_id),
            "assignment_id": str(assignment.id),
            "delivery_objectives": assignment.delivery_objectives,
            "required_competency_ids": assignment.required_competency_ids,
            "adaptation_boundary": "INSTITUTIONAL_AUTHORITY",
        }
