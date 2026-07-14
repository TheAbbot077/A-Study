from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from apps.academic.domain.models import ContentConcept, LearningResource
from apps.assessments.domain.models import MasteryDecisionValue, MasteryProfile
from apps.learning.domain.models import PedagogicalSession, PedagogicalState
from apps.learning.services.pedagogical_session_service import PedagogicalSessionService
from apps.remediation.domain.models import RemediationPlan, RemediationPlanStatus
from apps.users.domain.models import User


@dataclass(frozen=True)
class ConceptBrowserState:
    concept_id: str
    status: str
    can_start_or_resume: bool
    action_label: str | None = None
    session_id: str | None = None
    session_status: str | None = None
    mastery_decision: str | None = None
    remediation_plan_id: str | None = None


class ConceptBrowserService:
    def __init__(self, session_service: Optional[PedagogicalSessionService] = None) -> None:
        self.session_service = session_service or PedagogicalSessionService()

    def list_resource_concept_states(self, learner: User, learning_resource: LearningResource) -> list[ConceptBrowserState]:
        concepts = list(
            ContentConcept.objects.filter(content_section__learning_resource=learning_resource)
            .select_related("content_section")
            .order_by("content_section__sequence_number", "sequence_number")
        )
        if not concepts:
            return []

        concept_ids = [concept.id for concept in concepts]
        mastery_profiles = {
            profile.content_concept_id: profile
            for profile in MasteryProfile.objects.filter(learner=learner, content_concept_id__in=concept_ids)
        }
        remediation_plans = self._active_remediation_plans(learner, concept_ids)
        sessions = self._latest_sessions(learner, concept_ids)

        return [
            self._build_state(
                concept=concept,
                mastery_profile=mastery_profiles.get(concept.id),
                remediation_plan=remediation_plans.get(concept.id),
                session=sessions.get(concept.id),
            )
            for concept in concepts
        ]

    def start_or_resume_concept(self, learner: User, concept: ContentConcept) -> PedagogicalSession:
        state = self._build_state(
            concept=concept,
            mastery_profile=MasteryProfile.objects.filter(learner=learner, content_concept=concept).first(),
            remediation_plan=self._active_remediation_plans(learner, [concept.id]).get(concept.id),
            session=self._latest_sessions(learner, [concept.id]).get(concept.id),
        )
        if not state.can_start_or_resume:
            raise ValueError(f"Concept {concept.id} is not available for start or resume.")

        existing_session = self._latest_sessions(learner, [concept.id]).get(concept.id)
        if existing_session is None or existing_session.status in {PedagogicalState.COMPLETED, PedagogicalState.ABANDONED}:
            created_session = self.session_service.create_session(learner=learner, content_concept=concept)
            return self.session_service.start_session(created_session)
        if existing_session.status == PedagogicalState.CREATED:
            return self.session_service.start_session(existing_session)
        if existing_session.status == PedagogicalState.PAUSED:
            return self.session_service.resume_session(existing_session)
        return existing_session

    def _latest_sessions(self, learner: User, concept_ids: list) -> dict:
        sessions = (
            PedagogicalSession.objects.filter(learner=learner, content_concept_id__in=concept_ids)
            .order_by("content_concept_id", "-created_at")
        )
        latest = {}
        for session in sessions:
            latest.setdefault(session.content_concept_id, session)
        return latest

    def _active_remediation_plans(self, learner: User, concept_ids: list) -> dict:
        plans = (
            RemediationPlan.objects.filter(
                learner=learner,
                content_concept_id__in=concept_ids,
                status__in=[
                    RemediationPlanStatus.PENDING,
                    RemediationPlanStatus.ACTIVE,
                    RemediationPlanStatus.ESCALATED,
                ],
            )
            .order_by("content_concept_id", "-created_at")
        )
        latest = {}
        for plan in plans:
            latest.setdefault(plan.content_concept_id, plan)
        return latest

    def _build_state(
        self,
        concept: ContentConcept,
        mastery_profile: MasteryProfile | None,
        remediation_plan: RemediationPlan | None,
        session: PedagogicalSession | None,
    ) -> ConceptBrowserState:
        if not concept.is_active:
            return ConceptBrowserState(concept_id=str(concept.id), status="locked", can_start_or_resume=False)

        mastery_decision = mastery_profile.current_decision if mastery_profile else None
        if mastery_decision == MasteryDecisionValue.MASTERED:
            return ConceptBrowserState(
                concept_id=str(concept.id),
                status="mastered",
                can_start_or_resume=False,
                mastery_decision=mastery_decision,
            )

        if remediation_plan is not None:
            return ConceptBrowserState(
                concept_id=str(concept.id),
                status="needs_remediation",
                can_start_or_resume=False,
                mastery_decision=mastery_decision,
                remediation_plan_id=str(remediation_plan.id),
            )

        if session is not None and session.status in {
            PedagogicalState.CREATED,
            PedagogicalState.ACTIVE,
            PedagogicalState.PAUSED,
        }:
            action_label = "Resume concept" if session.status == PedagogicalState.PAUSED else "Continue concept"
            return ConceptBrowserState(
                concept_id=str(concept.id),
                status="in_progress",
                can_start_or_resume=True,
                action_label=action_label,
                session_id=str(session.id),
                session_status=session.status,
                mastery_decision=mastery_decision,
            )

        return ConceptBrowserState(
            concept_id=str(concept.id),
            status="available",
            can_start_or_resume=True,
            action_label="Start concept",
            mastery_decision=mastery_decision,
        )
