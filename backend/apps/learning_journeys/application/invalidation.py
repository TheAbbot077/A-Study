from __future__ import annotations

from dataclasses import dataclass

from ..domain.enums import LearningJourneyActionCode


@dataclass(frozen=True)
class DependencyInvalidationPlan:
    action_code: str
    invalidated_capabilities: tuple[str, ...]
    reason: str

    def to_metadata(self) -> dict:
        return {
            "action_code": self.action_code,
            "invalidated_capabilities": list(self.invalidated_capabilities),
            "reason": self.reason,
        }


class SelfStudyJourneyDependencyInvalidationPolicy:
    """Documents downstream effects without deleting historical source records."""

    def plan_for(self, *, action_code: str, payload: dict) -> DependencyInvalidationPlan:
        if action_code != LearningJourneyActionCode.REVISE_INTENT:
            return DependencyInvalidationPlan(action_code=action_code, invalidated_capabilities=(), reason="NO_INVALIDATION_REQUIRED")

        fields = set((payload or {}).get("changes", {}).keys())
        if fields & {"topic_query", "study_intent", "qualification_query", "jurisdiction_query", "awarding_body_query", "level_query"}:
            return DependencyInvalidationPlan(
                action_code=action_code,
                invalidated_capabilities=(
                    "curriculum_resolution",
                    "curriculum_selection",
                    "subject_binding",
                    "diagnostic",
                    "bridge_plan",
                    "learning_plan",
                    "teaching_preparation",
                    "teaching_session",
                ),
                reason="INTENT_ACADEMIC_TARGET_CHANGED",
            )
        if fields & {"target_date", "weekly_study_minutes"}:
            return DependencyInvalidationPlan(
                action_code=action_code,
                invalidated_capabilities=("learning_plan", "teaching_preparation"),
                reason="INTENT_SCHEDULE_CHANGED",
            )
        return DependencyInvalidationPlan(action_code=action_code, invalidated_capabilities=(), reason="INTENT_CHANGE_DOES_NOT_INVALIDATE_DOWNSTREAM")
