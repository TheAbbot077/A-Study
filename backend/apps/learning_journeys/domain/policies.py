from __future__ import annotations

from .enums import LearningJourneyStatus
from .exceptions import LearningJourneyTransitionError


TERMINAL_STATUSES = {
    LearningJourneyStatus.LEARNING_GOAL_COMPLETED,
    LearningJourneyStatus.WITHDRAWN,
    LearningJourneyStatus.ARCHIVED,
}


VALID_TRANSITIONS = {
    LearningJourneyStatus.CREATED: {
        LearningJourneyStatus.DISCOVERING_GOAL,
        LearningJourneyStatus.SUBJECT_BINDING_REQUIRED,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.DISCOVERING_GOAL: {
        LearningJourneyStatus.INTENT_CONFIRMED,
        LearningJourneyStatus.RESOLVING_CURRICULUM,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.INTENT_CONFIRMED: {
        LearningJourneyStatus.RESOLVING_CURRICULUM,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.RESOLVING_CURRICULUM: {
        LearningJourneyStatus.CURRICULUM_MATCHED,
        LearningJourneyStatus.CURRICULUM_UNRESOLVED,
        LearningJourneyStatus.SUBJECT_BINDING_UNAVAILABLE,
        LearningJourneyStatus.SUBJECT_BOUND,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.CURRICULUM_UNRESOLVED: {
        LearningJourneyStatus.RESOLVING_CURRICULUM,
        LearningJourneyStatus.DISCOVERING_GOAL,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.CURRICULUM_MATCHED: {
        LearningJourneyStatus.SUBJECT_BOUND,
        LearningJourneyStatus.SUBJECT_BINDING_REQUIRED,
        LearningJourneyStatus.SUBJECT_BINDING_UNAVAILABLE,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.SUBJECT_BINDING_REQUIRED: {
        LearningJourneyStatus.SUBJECT_BOUND,
        LearningJourneyStatus.SUBJECT_BINDING_UNAVAILABLE,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.SUBJECT_BINDING_UNAVAILABLE: {
        LearningJourneyStatus.RESOLVING_CURRICULUM,
        LearningJourneyStatus.SUBJECT_BOUND,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.SUBJECT_BOUND: {
        LearningJourneyStatus.STARTING_STATE_REQUIRED,
        LearningJourneyStatus.PLAN_REQUIRED,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.STARTING_STATE_REQUIRED: {
        LearningJourneyStatus.STARTING_STATE_IN_PROGRESS,
        LearningJourneyStatus.STARTING_STATE_CONFIRMED,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.STARTING_STATE_IN_PROGRESS: {
        LearningJourneyStatus.STARTING_STATE_CONFIRMED,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.STARTING_STATE_CONFIRMED: {
        LearningJourneyStatus.BRIDGE_REQUIRED,
        LearningJourneyStatus.PLAN_REQUIRED,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.BRIDGE_REQUIRED: {
        LearningJourneyStatus.PLAN_REQUIRED,
        LearningJourneyStatus.PLAN_READY,
        LearningJourneyStatus.LEARNING_BLOCKED,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.PLAN_REQUIRED: {
        LearningJourneyStatus.PLAN_READY,
        LearningJourneyStatus.LEARNING_BLOCKED,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.PLAN_READY: {
        LearningJourneyStatus.LEARNING_ACTIVE,
        LearningJourneyStatus.LEARNING_BLOCKED,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.LEARNING_ACTIVE: {
        LearningJourneyStatus.LEARNING_BLOCKED,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.LEARNING_GOAL_COMPLETED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.LEARNING_BLOCKED: {
        LearningJourneyStatus.LEARNING_ACTIVE,
        LearningJourneyStatus.PLAN_READY,
        LearningJourneyStatus.PAUSED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
    LearningJourneyStatus.PAUSED: {
        LearningJourneyStatus.DISCOVERING_GOAL,
        LearningJourneyStatus.RESOLVING_CURRICULUM,
        LearningJourneyStatus.SUBJECT_BOUND,
        LearningJourneyStatus.STARTING_STATE_REQUIRED,
        LearningJourneyStatus.STARTING_STATE_IN_PROGRESS,
        LearningJourneyStatus.BRIDGE_REQUIRED,
        LearningJourneyStatus.PLAN_REQUIRED,
        LearningJourneyStatus.PLAN_READY,
        LearningJourneyStatus.LEARNING_ACTIVE,
        LearningJourneyStatus.LEARNING_BLOCKED,
        LearningJourneyStatus.WITHDRAWN,
        LearningJourneyStatus.ARCHIVED,
    },
}


class LearningJourneyLifecyclePolicy:
    @classmethod
    def can_transition(cls, source: str, target: str) -> bool:
        if source == target:
            return True
        if source in TERMINAL_STATUSES:
            return False
        return target in VALID_TRANSITIONS.get(source, set())

    @classmethod
    def validate(cls, source: str, target: str) -> None:
        if not cls.can_transition(source, target):
            raise LearningJourneyTransitionError(
                f"Learning journey cannot transition from {source} to {target}.",
                code="INVALID_LEARNING_JOURNEY_TRANSITION",
            )
