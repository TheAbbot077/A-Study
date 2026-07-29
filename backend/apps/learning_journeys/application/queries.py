from __future__ import annotations

from django.core.exceptions import PermissionDenied

from apps.users.domain.models import InstitutionMembership, InstitutionRole

from ..domain.enums import LearningCompetencyProgressState, LearningCompetencyUnlockState, LearningJourneySourceType
from ..domain.models import InstitutionalLearningAssignment, LearningCompetencyProgress, LearningJourney, LearningJourneySourceBinding
from .adapters import InstitutionalJourneyAdapter, SelfStudyJourneyAdapter
from .services import can_read_journey


class LearningJourneyReadPresenter:
    def present(self, journey: LearningJourney) -> dict:
        projection = self._projection(journey)
        active_binding = journey.subject_bindings.select_related("subject", "curriculum_reference").filter(status="ACTIVE").first()
        state = projection.status
        status_reason = projection.status_reason.to_dict()
        actions = [action.to_dict() for action in projection.available_actions]
        blockers = [blocker.to_dict() for blocker in projection.blockers]
        if journey.status in {"PAUSED", "WITHDRAWN", "ARCHIVED"}:
            state = journey.status
            status_reason = {"code": journey.status_reason_code}
            if journey.status == "PAUSED":
                actions = [
                    {
                        "code": "RESUME_JOURNEY",
                        "label": "Resume journey",
                        "method": "POST",
                        "endpoint_name": "learning-journey-resume",
                        "enabled": True,
                        "disabled_reason": "",
                        "requires_confirmation": False,
                    }
                ]
            else:
                actions = []
            blockers = blockers if journey.status == "PAUSED" else []
        payload = {
            "journey_id": str(journey.id),
            "journey_type": journey.journey_type,
            "state": state,
            "status_reason": status_reason,
            "current_step": projection.current_step.to_dict(),
            "subject": projection.subject,
            "authority": projection.authority,
            "available_actions": actions,
            "blockers": blockers,
            "capability_references": projection.capability_references,
            "active_capabilities": self._active_capabilities(projection.capability_references),
            "progress": self._progress(state),
            "competency_context": self._competency_context(journey),
            "institutional_state": self._institutional_state(journey),
            "version": journey.version,
            "last_synchronized_at": journey.last_synchronized_at.isoformat() if journey.last_synchronized_at else None,
        }
        if active_binding and not payload["subject"]:
            payload["subject"] = {"id": str(active_binding.subject_id), "name": active_binding.subject.name}
        return payload

    def _active_capabilities(self, references: dict) -> dict:
        return {
            "intent_id": references.get("intent_id") or None,
            "curriculum_resolution_attempt_id": references.get("curriculum_resolution_attempt_id") or None,
            "diagnostic_id": references.get("diagnostic_id") or None,
            "placement_id": references.get("placement_id") or None,
            "bridge_plan_id": references.get("bridge_plan_id") or None,
            "learning_plan_id": references.get("learning_plan_id") or None,
            "teaching_preparation_id": references.get("teaching_preparation_id") or None,
            "active_teaching_session_id": references.get("active_teaching_session_id") or None,
        }

    def _progress(self, state: str) -> dict:
        phases = [
            ("GOAL_DISCOVERY", {"CREATED", "DISCOVERING_GOAL", "INTENT_CONFIRMED"}),
            ("CURRICULUM", {"RESOLVING_CURRICULUM", "CURRICULUM_UNRESOLVED", "CURRICULUM_MATCHED", "SUBJECT_BINDING_REQUIRED", "SUBJECT_BINDING_UNAVAILABLE", "SUBJECT_BOUND"}),
            ("STARTING_STATE", {"STARTING_STATE_REQUIRED", "STARTING_STATE_IN_PROGRESS", "STARTING_STATE_CONFIRMED"}),
            ("BRIDGE", {"BRIDGE_REQUIRED"}),
            ("PLANNING", {"PLAN_REQUIRED", "PLAN_READY"}),
            ("LEARNING", {"LEARNING_ACTIVE", "LEARNING_BLOCKED", "PAUSED"}),
            ("COMPLETED", {"LEARNING_GOAL_COMPLETED", "WITHDRAWN", "ARCHIVED"}),
        ]
        for index, (phase, states) in enumerate(phases, start=1):
            if state in states:
                return {
                    "phase": phase,
                    "completed_steps": max(0, index - 1),
                    "total_known_steps": len(phases),
                    "is_exact_total": False,
                }
        return {
            "phase": "GOAL_DISCOVERY",
            "completed_steps": 0,
            "total_known_steps": len(phases),
            "is_exact_total": False,
        }

    def _competency_context(self, journey: LearningJourney) -> dict:
        rows = list(
            LearningCompetencyProgress.objects.select_related("competency")
            .filter(journey=journey)
            .order_by("competency__ordinal", "competency__stable_key")
        )
        completed_states = {LearningCompetencyProgressState.DEMONSTRATED, LearningCompetencyProgressState.REINFORCED}
        active_rows = [row for row in rows if row.unlock_state == LearningCompetencyUnlockState.ACTIVE]
        available_rows = [row for row in rows if row.unlock_state == LearningCompetencyUnlockState.AVAILABLE]
        review_rows = [row for row in rows if row.state == LearningCompetencyProgressState.REVIEW_REQUIRED]
        return {
            "current_learning_phase": self._competency_phase(active_rows=active_rows, available_rows=available_rows, review_rows=review_rows, rows=rows),
            "active_competency": self._competency_row((active_rows or available_rows or [None])[0]),
            "next_competency": self._competency_row((available_rows or [None])[0]),
            "blocked_competencies": [self._competency_row(row) for row in review_rows],
            "available_competencies": [self._competency_row(row) for row in available_rows],
            "completed_competency_count": sum(1 for row in rows if row.state in completed_states),
        }

    def _competency_phase(self, *, active_rows: list, available_rows: list, review_rows: list, rows: list) -> str:
        if review_rows:
            return "REVIEW"
        if active_rows or available_rows:
            return "LEARNING"
        if rows:
            return "PROGRESSING"
        return "NOT_STARTED"

    def _competency_row(self, row: LearningCompetencyProgress | None) -> dict | None:
        if not row:
            return None
        return {
            "progress_id": str(row.id),
            "competency_id": str(row.competency_id),
            "stable_key": row.competency.stable_key,
            "title": row.competency.title,
            "state": row.state,
            "unlock_state": row.unlock_state,
        }

    def _institutional_state(self, journey: LearningJourney) -> dict | None:
        assignment = InstitutionalLearningAssignment.objects.select_related("institution", "subject", "curriculum_reference").filter(journey=journey).first()
        if not assignment:
            return None
        return {
            "assignment": assignment.assignment_state,
            "completion": assignment.completion_state,
            "institution": {"id": str(assignment.institution_id), "name": assignment.institution.name},
            "programme": assignment.programme_label,
            "course": assignment.course_label,
            "subject": {"id": str(assignment.subject_id), "name": assignment.subject.name} if assignment.subject_id else None,
            "curriculum": {"id": str(assignment.curriculum_reference_id), "title": assignment.curriculum_reference.title}
            if assignment.curriculum_reference_id
            else None,
        }

    def _projection(self, journey: LearningJourney):
        binding = journey.source_bindings.first()
        if not binding:
            return InstitutionalJourneyAdapter().project()
        if binding.source_type == LearningJourneySourceType.SELF_STUDY_WORKSPACE:
            from apps.self_study.workspace_models import SelfStudyWorkspace

            workspace = SelfStudyWorkspace.objects.select_related(
                "tenant",
                "learner",
                "intent",
                "curriculum_resolution",
                "active_diagnostic",
                "active_bridge_plan",
                "active_teaching_preparation",
                "active_teaching_session",
            ).get(id=binding.source_id)
            return SelfStudyJourneyAdapter(workspace=workspace).project()
        if binding.source_type == LearningJourneySourceType.INSTITUTIONAL_ASSIGNMENT:
            assignment = InstitutionalLearningAssignment.objects.select_related(
                "institution",
                "membership",
                "learner",
                "subject",
                "curriculum_reference",
                "journey",
            ).get(id=binding.source_id)
            return InstitutionalJourneyAdapter(assignment=assignment).project()
        if binding.source_type == LearningJourneySourceType.INSTITUTION_MEMBERSHIP:
            membership = InstitutionMembership.objects.select_related("institution", "user").get(id=binding.source_id)
            assignment = InstitutionalLearningAssignment.objects.select_related(
                "institution",
                "membership",
                "learner",
                "subject",
                "curriculum_reference",
                "journey",
            ).filter(membership=membership).first()
            return InstitutionalJourneyAdapter(assignment=assignment, membership=membership).project()
        return InstitutionalJourneyAdapter().project()


class GetLearningJourneyService:
    def execute(self, *, journey_id, actor) -> dict:
        journey = LearningJourney.objects.select_related("learner", "institution").get(id=journey_id)
        if not can_read_journey(actor, journey):
            raise PermissionDenied("LEARNING_JOURNEY_PERMISSION_DENIED")
        return LearningJourneyReadPresenter().present(journey)


class ListLearnerJourneysService:
    def execute(self, *, actor) -> list[dict]:
        queryset = LearningJourney.objects.select_related("learner", "institution").order_by("-updated_at")
        if not actor.is_superuser:
            institution_ids = list(
                InstitutionMembership.objects.filter(
                    user=actor,
                    is_active=True,
                    role__in=[
                        InstitutionRole.ADMINISTRATOR,
                        InstitutionRole.INSTITUTION_OWNER,
                        InstitutionRole.SYSTEM_ADMINISTRATOR,
                        InstitutionRole.TEACHER,
                    ],
                ).values_list("institution_id", flat=True)
            )
            queryset = queryset.filter(learner=actor) | queryset.filter(institution_id__in=institution_ids)
        journey_ids = list(queryset.distinct().values_list("id", flat=True))
        return [GetLearningJourneyService().execute(journey_id=journey_id, actor=actor) for journey_id in journey_ids]


def source_binding_for_self_study_workspace(*, workspace_id):
    return LearningJourneySourceBinding.objects.filter(
        source_type=LearningJourneySourceType.SELF_STUDY_WORKSPACE,
        source_id=workspace_id,
    ).select_related("journey").first()
