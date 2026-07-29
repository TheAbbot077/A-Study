from __future__ import annotations

from dataclasses import dataclass

from apps.assessments.domain.models import MasteryDecision, MasteryDecisionValue

from ..domain.enums import (
    LearningCompetencyProgressReason,
    LearningCompetencyProgressState,
    LearningCompetencyUnlockState,
)


VALID_TRANSITIONS = {
    LearningCompetencyProgressState.NOT_STARTED: {
        LearningCompetencyProgressState.EMERGING,
        LearningCompetencyProgressState.DEVELOPING,
        LearningCompetencyProgressState.DEMONSTRATED,
        LearningCompetencyProgressState.REVIEW_REQUIRED,
        LearningCompetencyProgressState.SUPERSEDED,
    },
    LearningCompetencyProgressState.EMERGING: {
        LearningCompetencyProgressState.DEVELOPING,
        LearningCompetencyProgressState.DEMONSTRATED,
        LearningCompetencyProgressState.REVIEW_REQUIRED,
        LearningCompetencyProgressState.REGRESSED,
        LearningCompetencyProgressState.SUPERSEDED,
    },
    LearningCompetencyProgressState.DEVELOPING: {
        LearningCompetencyProgressState.DEMONSTRATED,
        LearningCompetencyProgressState.REVIEW_REQUIRED,
        LearningCompetencyProgressState.REGRESSED,
        LearningCompetencyProgressState.SUPERSEDED,
    },
    LearningCompetencyProgressState.DEMONSTRATED: {
        LearningCompetencyProgressState.REINFORCED,
        LearningCompetencyProgressState.REVIEW_REQUIRED,
        LearningCompetencyProgressState.REGRESSED,
        LearningCompetencyProgressState.SUPERSEDED,
    },
    LearningCompetencyProgressState.REINFORCED: {
        LearningCompetencyProgressState.REVIEW_REQUIRED,
        LearningCompetencyProgressState.REGRESSED,
        LearningCompetencyProgressState.SUPERSEDED,
    },
    LearningCompetencyProgressState.REVIEW_REQUIRED: {
        LearningCompetencyProgressState.DEVELOPING,
        LearningCompetencyProgressState.DEMONSTRATED,
        LearningCompetencyProgressState.REGRESSED,
        LearningCompetencyProgressState.SUPERSEDED,
    },
    LearningCompetencyProgressState.REGRESSED: {
        LearningCompetencyProgressState.DEVELOPING,
        LearningCompetencyProgressState.REVIEW_REQUIRED,
        LearningCompetencyProgressState.SUPERSEDED,
    },
    LearningCompetencyProgressState.SUPERSEDED: set(),
}


@dataclass(frozen=True)
class ProgressionDecision:
    state: str
    unlock_state: str
    reason: str
    changed: bool


class CompetencyProgressionPolicy:
    def decide(self, *, current_state: str, current_unlock_state: str, mastery_decision: MasteryDecision) -> ProgressionDecision:
        target = current_state
        reason = LearningCompetencyProgressReason.UNCHANGED
        unlock_state = current_unlock_state

        if mastery_decision.decision == MasteryDecisionValue.MASTERED:
            if current_state in {LearningCompetencyProgressState.DEMONSTRATED, LearningCompetencyProgressState.REINFORCED}:
                target = LearningCompetencyProgressState.REINFORCED
                reason = LearningCompetencyProgressReason.MASTERY_REINFORCED
            else:
                target = LearningCompetencyProgressState.DEMONSTRATED
                reason = LearningCompetencyProgressReason.MASTERY_DEMONSTRATED
            unlock_state = LearningCompetencyUnlockState.COMPLETED
        elif mastery_decision.decision == MasteryDecisionValue.EMERGING:
            target = LearningCompetencyProgressState.DEVELOPING if current_state != LearningCompetencyProgressState.NOT_STARTED else LearningCompetencyProgressState.EMERGING
            reason = LearningCompetencyProgressReason.MASTERY_EMERGING
            if current_unlock_state in {LearningCompetencyUnlockState.LOCKED, LearningCompetencyUnlockState.AVAILABLE}:
                unlock_state = LearningCompetencyUnlockState.ACTIVE
        elif mastery_decision.decision == MasteryDecisionValue.NEEDS_REVIEW:
            target = LearningCompetencyProgressState.REVIEW_REQUIRED
            reason = LearningCompetencyProgressReason.REVIEW_REQUIRED
            unlock_state = LearningCompetencyUnlockState.ACTIVE
        elif mastery_decision.decision == MasteryDecisionValue.NOT_MASTERED and current_state in {
            LearningCompetencyProgressState.DEVELOPING,
            LearningCompetencyProgressState.DEMONSTRATED,
            LearningCompetencyProgressState.REINFORCED,
            LearningCompetencyProgressState.REVIEW_REQUIRED,
        }:
            target = LearningCompetencyProgressState.REGRESSED
            reason = LearningCompetencyProgressReason.REGRESSION_EVIDENCE
            unlock_state = LearningCompetencyUnlockState.ACTIVE

        self.validate(current_state, target)
        return ProgressionDecision(
            state=target,
            unlock_state=unlock_state,
            reason=reason,
            changed=target != current_state or unlock_state != current_unlock_state,
        )

    def validate(self, source: str, target: str) -> None:
        if source == target:
            return
        if target not in VALID_TRANSITIONS.get(source, set()):
            from django.core.exceptions import ValidationError

            raise ValidationError("Competency progression transition is invalid.", code="COMPETENCY_PROGRESSION_INVALID")

    def supersede(self, *, current_state: str, current_unlock_state: str) -> ProgressionDecision:
        self.validate(current_state, LearningCompetencyProgressState.SUPERSEDED)
        return ProgressionDecision(
            state=LearningCompetencyProgressState.SUPERSEDED,
            unlock_state=LearningCompetencyUnlockState.SUPERSEDED,
            reason=LearningCompetencyProgressReason.CURRICULUM_SUPERSEDED,
            changed=current_state != LearningCompetencyProgressState.SUPERSEDED or current_unlock_state != LearningCompetencyUnlockState.SUPERSEDED,
        )
