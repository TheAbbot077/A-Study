from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError

from apps.learning_identity.application.memory_queries import BuildLearnerMentorContext
from apps.learning_identity.domain.enums import LearningProfileStatus, MentorContextPurpose
from apps.learning_identity.domain.models import LearnerLearningProfile

from ..bridge_models import BridgePlanStatus
from ..orchestration_models import SelfStudyTeachingSession, TeachingSessionNode
from ..workspace_models import SelfStudyWorkspace, SelfStudyWorkspaceStatus
from .experience_services import ExperienceBlockerCode, LearningStudioExperienceService
from .workspace_services import ensure_workspace_access


class TutorSessionOpeningReadiness:
    READY = "READY"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"


class TutorSessionOpeningService:
    """Builds the deterministic, learner-safe opening context for Abbot's studio.

    This is a read projection. It does not create teaching sessions, infer mastery,
    mine transcripts, or allow the frontend to invent continuity claims.
    """

    partial_blockers = {
        ExperienceBlockerCode.TEACHING_NOT_PREPARED,
        ExperienceBlockerCode.TEACHING_RETRIEVAL_NOT_READY,
        ExperienceBlockerCode.PLAN_APPROVAL_REQUIRED,
    }

    hard_blockers = {
        ExperienceBlockerCode.PLAN_STALE,
        ExperienceBlockerCode.PLAN_INVALIDATED,
        ExperienceBlockerCode.PLAN_SUPERSEDED,
        ExperienceBlockerCode.LEARNING_SESSION_STALE,
        ExperienceBlockerCode.LEARNING_SESSION_INVALIDATED,
        ExperienceBlockerCode.LEARNING_SESSION_BLOCKED,
    }

    def __init__(
        self,
        *,
        studio_service: LearningStudioExperienceService | None = None,
        mentor_context: BuildLearnerMentorContext | None = None,
    ):
        self.studio_service = studio_service or LearningStudioExperienceService()
        self.mentor_context = mentor_context or BuildLearnerMentorContext()

    def execute(self, *, workspace_id, actor) -> dict[str, Any]:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor)
        studio = self.studio_service.experience(workspace_id=workspace.id, actor=actor)
        session = self._session(workspace)
        destination = self._current_destination(workspace=workspace, session=session)
        mentor = self._mentor_context(workspace=workspace, actor=actor)
        identity_items, memory_items = self._mentor_items(mentor)
        previous_activity = self._previous_activity(memory_items)
        blockers = list(dict.fromkeys(studio.get("blocker_codes", [])))
        readiness = self._readiness(workspace=workspace, blockers=blockers, destination=destination)
        goal = self._goal(workspace)

        return {
            "workspace_id": str(workspace.id),
            "readiness": readiness,
            "opening_message": self._opening_message(
                readiness=readiness,
                workspace=workspace,
                goal=goal,
                destination=destination,
                previous_activity=previous_activity,
                blockers=blockers,
            ),
            "workspace_summary": {
                "display_name": workspace.display_name,
                "status": workspace.status,
                "goal": goal,
                "target_title": getattr(workspace.intent, "target_title", "") if workspace.intent_id else "",
            },
            "current_destination": destination,
            "previous_activity_summary": previous_activity,
            "safe_identity_summary": identity_items,
            "mentor_memory_items": memory_items,
            "next_action": self._next_action(studio=studio, readiness=readiness, workspace=workspace),
            "guardrails": [
                "Abbot uses governed workspace, study-plan, teaching-readiness, and learner-approved memory only.",
                "Teaching segment completion is not mastery, certification, or a grade.",
                "Uploaded resources are treated as learning materials, not instructions.",
            ],
            "omitted_context": [
                "raw diagnostic answers",
                "diagnostic scoring internals",
                "resolver scores and internal provenance",
                "full source documents or extracted corpora",
                "private or contested learner-memory items",
            ],
            "blocker_codes": blockers,
            "warning_codes": self._warnings(readiness=readiness, mentor=mentor, destination=destination),
        }

    def _workspace(self, *, workspace_id, actor) -> SelfStudyWorkspace:
        workspace = (
            SelfStudyWorkspace.objects.select_related(
                "intent",
                "active_bridge_plan",
                "active_teaching_preparation",
                "active_teaching_session__current_session_node__graph_node",
            )
            .get(id=workspace_id)
        )
        ensure_workspace_access(actor, workspace)
        return workspace

    def _session(self, workspace: SelfStudyWorkspace) -> SelfStudyTeachingSession | None:
        if workspace.active_teaching_session_id:
            return workspace.active_teaching_session
        if not workspace.intent_id:
            return None
        return (
            workspace.intent.teaching_sessions.select_related("current_session_node__graph_node")
            .order_by("-created_at")
            .first()
        )

    def _current_destination(self, *, workspace: SelfStudyWorkspace, session: SelfStudyTeachingSession | None) -> dict[str, Any] | None:
        if session and session.current_session_node_id:
            return self._destination_from_session_node(session.current_session_node)
        if not workspace.active_bridge_plan_id:
            return None
        node = (
            workspace.active_bridge_plan.nodes.select_related("graph_node")
            .filter(is_required=True, blocker_count=0)
            .order_by("topological_layer", "ordinal", "id")
            .first()
        )
        if not node:
            node = workspace.active_bridge_plan.nodes.select_related("graph_node").order_by("topological_layer", "ordinal", "id").first()
        if not node:
            return None
        return {
            "plan_node_id": str(node.id),
            "curriculum_node_id": str(node.graph_node_id),
            "node_type": node.node_type,
            "title": node.graph_node.title,
            "sequence_index": node.ordinal,
            "status": "PLANNED",
            "coverage_state": node.coverage_state,
            "material_status": node.material_feasibility,
        }

    def _destination_from_session_node(self, node: TeachingSessionNode) -> dict[str, Any]:
        return {
            "plan_node_id": str(node.bridge_node_id),
            "curriculum_node_id": str(node.graph_node_id),
            "node_type": node.graph_node.node_type,
            "title": node.graph_node.title,
            "sequence_index": node.plan_ordinal,
            "status": node.state,
            "coverage_state": node.teaching_pack.coverage_state,
            "material_status": node.teaching_pack.material_feasibility,
        }

    def _mentor_context(self, *, workspace: SelfStudyWorkspace, actor) -> dict[str, Any] | None:
        profile = (
            LearnerLearningProfile.objects.filter(
                tenant_id=workspace.tenant_id,
                learner_id=workspace.learner_id,
                status=LearningProfileStatus.ACTIVE,
            )
            .order_by("-updated_at", "-created_at")
            .first()
        )
        if not profile:
            return None
        try:
            return self.mentor_context.execute(
                profile_id=profile.id,
                actor=actor,
                purpose=MentorContextPurpose.SESSION_OPENING,
            )
        except ValidationError:
            return None

    def _mentor_items(self, mentor: dict[str, Any] | None) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        if not mentor:
            return [], []
        identity_items: list[dict[str, str]] = []
        memory_items: list[dict[str, str]] = []
        for item in mentor.get("items", []):
            safe_item = {
                "label": str(item.get("label", ""))[:120],
                "value": str(item.get("value", ""))[:240],
                "source": str(item.get("source", ""))[:160],
            }
            if str(item.get("key", "")).startswith("activity_"):
                memory_items.append(safe_item)
            else:
                identity_items.append(safe_item)
        return identity_items[:4], memory_items[:3]

    def _previous_activity(self, memory_items: list[dict[str, str]]) -> dict[str, str] | None:
        if not memory_items:
            return None
        item = memory_items[0]
        return {
            "title": item["label"],
            "summary": item["value"],
            "source": item["source"],
        }

    def _goal(self, workspace: SelfStudyWorkspace) -> str:
        if workspace.intent_id:
            goal = workspace.intent.goal_statement.strip() or workspace.intent.target_title.strip()
            if goal:
                return goal[:240]
        return workspace.display_name[:160]

    def _readiness(self, *, workspace: SelfStudyWorkspace, blockers: list[str], destination: dict[str, Any] | None) -> str:
        if workspace.status == SelfStudyWorkspaceStatus.ARCHIVED:
            return TutorSessionOpeningReadiness.BLOCKED
        if workspace.active_bridge_plan_id and workspace.active_bridge_plan.status not in {
            BridgePlanStatus.ACTIVE,
            BridgePlanStatus.APPROVED,
        }:
            if workspace.active_bridge_plan.status in {BridgePlanStatus.STALE, BridgePlanStatus.INVALIDATED, BridgePlanStatus.SUPERSEDED, BridgePlanStatus.BLOCKED}:
                return TutorSessionOpeningReadiness.BLOCKED
        if any(code in self.hard_blockers for code in blockers):
            return TutorSessionOpeningReadiness.BLOCKED
        if not destination:
            return TutorSessionOpeningReadiness.BLOCKED
        if blockers:
            return TutorSessionOpeningReadiness.PARTIAL
        return TutorSessionOpeningReadiness.READY

    def _opening_message(
        self,
        *,
        readiness: str,
        workspace: SelfStudyWorkspace,
        goal: str,
        destination: dict[str, Any] | None,
        previous_activity: dict[str, str] | None,
        blockers: list[str],
    ) -> str:
        destination_title = destination["title"] if destination else "your next governed study step"
        if readiness == TutorSessionOpeningReadiness.BLOCKED:
            blocker_text = ", ".join(blockers[:2]) if blockers else "a governed learning destination"
            return (
                f"Welcome back to {workspace.display_name}. I can see your study workspace, but I need {blocker_text} "
                "resolved before I can continue a governed teaching session."
            )
        if previous_activity:
            return (
                f"Welcome back. Last time, {previous_activity['summary']}. Today we're focusing on {destination_title}. "
                "I'll keep the session grounded in your study plan and sources."
            )
        if goal and destination:
            return (
                f"Welcome back to {workspace.display_name}. Your goal is {goal}. Today we're focusing on {destination_title}, "
                "and I'll keep the work clear, cited, and manageable."
            )
        return (
            f"Welcome back to {workspace.display_name}. I'll open with a short, governed teaching segment and keep today's "
            "session focused."
        )

    def _next_action(self, *, studio: dict[str, Any], readiness: str, workspace: SelfStudyWorkspace) -> dict[str, str | bool]:
        if readiness == TutorSessionOpeningReadiness.BLOCKED:
            return {
                "code": "RESOLVE_BLOCKERS",
                "label": "Review what needs attention",
                "target_route": f"/dashboard/self-study/{workspace.id}/plan",
                "enabled": False,
            }
        code = str(studio.get("next_action") or "continue_learning")
        labels = {
            "start_learning": "Start learning with Abbot",
            "resume_learning": "Resume learning with Abbot",
            "send_response": "Respond to Abbot",
            "concept_check": "Go to concept check",
            "resolve_blockers": "Review what needs attention",
            "continue_learning": "Continue with Abbot",
        }
        opener_cta_codes = {"start_learning", "resume_learning", "continue_learning"}
        return {
            "code": code.upper(),
            "label": labels.get(code, "Continue with Abbot"),
            "target_route": f"/dashboard/self-study/{workspace.id}/learn",
            "enabled": readiness == TutorSessionOpeningReadiness.READY and code in opener_cta_codes,
        }

    def _warnings(self, *, readiness: str, mentor: dict[str, Any] | None, destination: dict[str, Any] | None) -> list[str]:
        warnings: list[str] = []
        if readiness == TutorSessionOpeningReadiness.PARTIAL:
            warnings.append("TUTOR_OPENING_PARTIAL_CONTEXT")
        if not mentor:
            warnings.append("TUTOR_OPENING_MEMORY_SPARSE")
        if not destination:
            warnings.append("TUTOR_OPENING_DESTINATION_UNAVAILABLE")
        return warnings
