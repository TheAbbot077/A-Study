from __future__ import annotations

from django.core.exceptions import PermissionDenied

from apps.users.domain.models import InstitutionMembership, InstitutionRole

from ..domain.enums import LearningJourneySourceType
from ..domain.models import LearningJourney, LearningJourneySourceBinding
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
            "version": journey.version,
            "last_synchronized_at": journey.last_synchronized_at.isoformat() if journey.last_synchronized_at else None,
        }
        if active_binding and not payload["subject"]:
            payload["subject"] = {"id": str(active_binding.subject_id), "name": active_binding.subject.name}
        return payload

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
