from __future__ import annotations

from dataclasses import dataclass

from ..domain.enums import LearningJourneyActionCode, LearningJourneyStatus, LearningJourneyType
from ..domain.models import LearningJourney
from ..domain.value_objects import AvailableAction


ACTION_COPY = {
    LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY: "Get started",
    LearningJourneyActionCode.CONTINUE_GOAL_DISCOVERY: "Continue setup",
    LearningJourneyActionCode.CONFIRM_INTENT: "Confirm goal",
    LearningJourneyActionCode.REVISE_INTENT: "Revise goal",
    LearningJourneyActionCode.RESOLVE_CURRICULUM: "Find curriculum",
    LearningJourneyActionCode.RETRY_CURRICULUM_RESOLUTION: "Try curriculum search again",
    LearningJourneyActionCode.SELECT_CURRICULUM: "Select curriculum",
    LearningJourneyActionCode.BEGIN_DIAGNOSTIC: "Begin diagnostic",
    LearningJourneyActionCode.CONTINUE_DIAGNOSTIC: "Continue diagnostic",
    LearningJourneyActionCode.CONFIRM_PLACEMENT: "Confirm placement",
    LearningJourneyActionCode.GENERATE_BRIDGE_PLAN: "Prepare bridge plan",
    LearningJourneyActionCode.GENERATE_LEARNING_PLAN: "Create study plan",
    LearningJourneyActionCode.ACTIVATE_LEARNING_PLAN: "Activate plan",
    LearningJourneyActionCode.PREPARE_TEACHING_SESSION: "Prepare teaching",
    LearningJourneyActionCode.BEGIN_TEACHING_SESSION: "Begin teaching session",
    LearningJourneyActionCode.CONTINUE_TEACHING_SESSION: "Continue teaching session",
    LearningJourneyActionCode.RETRY_BLOCKED_STEP: "Try again",
    LearningJourneyActionCode.PAUSE_JOURNEY: "Pause journey",
    LearningJourneyActionCode.RESUME_JOURNEY: "Resume journey",
    LearningJourneyActionCode.WITHDRAW_JOURNEY: "Withdraw journey",
    LearningJourneyActionCode.SYNCHRONIZE: "Refresh journey",
}

TERMINAL_STATUSES = {
    LearningJourneyStatus.LEARNING_GOAL_COMPLETED,
    LearningJourneyStatus.WITHDRAWN,
    LearningJourneyStatus.ARCHIVED,
}


@dataclass(frozen=True)
class JourneyActionDefinition:
    code: str
    allowed_statuses: frozenset[str]
    source_capability: str
    implemented: bool = True
    requires_confirmation: bool = False
    unavailable_reason: str = ""


SELF_STUDY_ACTIONS: dict[str, JourneyActionDefinition] = {
    LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY: JourneyActionDefinition(
        code=LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY,
        allowed_statuses=frozenset({LearningJourneyStatus.CREATED, LearningJourneyStatus.DISCOVERING_GOAL}),
        source_capability="self_study.onboarding",
    ),
    LearningJourneyActionCode.CONTINUE_GOAL_DISCOVERY: JourneyActionDefinition(
        code=LearningJourneyActionCode.CONTINUE_GOAL_DISCOVERY,
        allowed_statuses=frozenset({LearningJourneyStatus.DISCOVERING_GOAL}),
        source_capability="self_study.onboarding",
    ),
    LearningJourneyActionCode.CONFIRM_INTENT: JourneyActionDefinition(
        code=LearningJourneyActionCode.CONFIRM_INTENT,
        allowed_statuses=frozenset({LearningJourneyStatus.DISCOVERING_GOAL, LearningJourneyStatus.CURRICULUM_MATCHED}),
        source_capability="self_study.onboarding",
    ),
    LearningJourneyActionCode.REVISE_INTENT: JourneyActionDefinition(
        code=LearningJourneyActionCode.REVISE_INTENT,
        allowed_statuses=frozenset(
            {
                LearningJourneyStatus.INTENT_CONFIRMED,
                LearningJourneyStatus.RESOLVING_CURRICULUM,
                LearningJourneyStatus.CURRICULUM_UNRESOLVED,
                LearningJourneyStatus.CURRICULUM_MATCHED,
                LearningJourneyStatus.SUBJECT_BINDING_UNAVAILABLE,
                LearningJourneyStatus.SUBJECT_BOUND,
                LearningJourneyStatus.STARTING_STATE_REQUIRED,
                LearningJourneyStatus.PLAN_REQUIRED,
                LearningJourneyStatus.PLAN_READY,
            }
        ),
        source_capability="self_study.intent",
        implemented=False,
        unavailable_reason="Intent revision needs the source intent revision command for this workspace state.",
    ),
    LearningJourneyActionCode.RESOLVE_CURRICULUM: JourneyActionDefinition(
        code=LearningJourneyActionCode.RESOLVE_CURRICULUM,
        allowed_statuses=frozenset(
            {
                LearningJourneyStatus.DISCOVERING_GOAL,
                LearningJourneyStatus.INTENT_CONFIRMED,
                LearningJourneyStatus.RESOLVING_CURRICULUM,
                LearningJourneyStatus.CURRICULUM_UNRESOLVED,
            }
        ),
        source_capability="self_study.curriculum_resolution",
    ),
    LearningJourneyActionCode.RETRY_CURRICULUM_RESOLUTION: JourneyActionDefinition(
        code=LearningJourneyActionCode.RETRY_CURRICULUM_RESOLUTION,
        allowed_statuses=frozenset({LearningJourneyStatus.RESOLVING_CURRICULUM, LearningJourneyStatus.CURRICULUM_UNRESOLVED}),
        source_capability="self_study.curriculum_resolution",
    ),
    LearningJourneyActionCode.SELECT_CURRICULUM: JourneyActionDefinition(
        code=LearningJourneyActionCode.SELECT_CURRICULUM,
        allowed_statuses=frozenset({LearningJourneyStatus.CURRICULUM_MATCHED}),
        source_capability="self_study.curriculum_resolution",
    ),
    LearningJourneyActionCode.BEGIN_DIAGNOSTIC: JourneyActionDefinition(
        code=LearningJourneyActionCode.BEGIN_DIAGNOSTIC,
        allowed_statuses=frozenset({LearningJourneyStatus.SUBJECT_BOUND, LearningJourneyStatus.STARTING_STATE_REQUIRED}),
        source_capability="self_study.entry_diagnostic",
    ),
    LearningJourneyActionCode.CONTINUE_DIAGNOSTIC: JourneyActionDefinition(
        code=LearningJourneyActionCode.CONTINUE_DIAGNOSTIC,
        allowed_statuses=frozenset({LearningJourneyStatus.STARTING_STATE_IN_PROGRESS}),
        source_capability="self_study.entry_diagnostic",
    ),
    LearningJourneyActionCode.CONFIRM_PLACEMENT: JourneyActionDefinition(
        code=LearningJourneyActionCode.CONFIRM_PLACEMENT,
        allowed_statuses=frozenset({LearningJourneyStatus.STARTING_STATE_IN_PROGRESS, LearningJourneyStatus.STARTING_STATE_REQUIRED}),
        source_capability="self_study.entry_diagnostic",
    ),
    LearningJourneyActionCode.GENERATE_BRIDGE_PLAN: JourneyActionDefinition(
        code=LearningJourneyActionCode.GENERATE_BRIDGE_PLAN,
        allowed_statuses=frozenset({LearningJourneyStatus.BRIDGE_REQUIRED, LearningJourneyStatus.LEARNING_BLOCKED}),
        source_capability="self_study.bridge_plan",
        implemented=False,
        unavailable_reason="Bridge generation requires explicit target nodes from the bridge planning capability.",
    ),
    LearningJourneyActionCode.GENERATE_LEARNING_PLAN: JourneyActionDefinition(
        code=LearningJourneyActionCode.GENERATE_LEARNING_PLAN,
        allowed_statuses=frozenset({LearningJourneyStatus.PLAN_REQUIRED}),
        source_capability="self_study.learning_plan",
        implemented=False,
        unavailable_reason="Learning plan generation is represented by bridge-plan and teaching-preparation capabilities in this backend.",
    ),
    LearningJourneyActionCode.ACTIVATE_LEARNING_PLAN: JourneyActionDefinition(
        code=LearningJourneyActionCode.ACTIVATE_LEARNING_PLAN,
        allowed_statuses=frozenset({LearningJourneyStatus.PLAN_READY}),
        source_capability="self_study.learning_plan",
        implemented=False,
        unavailable_reason="Plan activation must be performed by the authoritative plan/teaching readiness capability.",
    ),
    LearningJourneyActionCode.PREPARE_TEACHING_SESSION: JourneyActionDefinition(
        code=LearningJourneyActionCode.PREPARE_TEACHING_SESSION,
        allowed_statuses=frozenset({LearningJourneyStatus.PLAN_READY, LearningJourneyStatus.LEARNING_ACTIVE, LearningJourneyStatus.LEARNING_BLOCKED}),
        source_capability="self_study.teaching_preparation",
        implemented=False,
        unavailable_reason="Teaching preparation requires a ready bridge plan and remains owned by teaching preparation services.",
    ),
    LearningJourneyActionCode.BEGIN_TEACHING_SESSION: JourneyActionDefinition(
        code=LearningJourneyActionCode.BEGIN_TEACHING_SESSION,
        allowed_statuses=frozenset({LearningJourneyStatus.LEARNING_ACTIVE}),
        source_capability="self_study.teaching_session",
        implemented=False,
        unavailable_reason="Teaching session creation remains owned by the teaching orchestration service.",
    ),
    LearningJourneyActionCode.CONTINUE_TEACHING_SESSION: JourneyActionDefinition(
        code=LearningJourneyActionCode.CONTINUE_TEACHING_SESSION,
        allowed_statuses=frozenset({LearningJourneyStatus.LEARNING_ACTIVE}),
        source_capability="self_study.teaching_session",
        implemented=False,
        unavailable_reason="Teaching turn continuation remains owned by the teaching orchestration service.",
    ),
    LearningJourneyActionCode.RETRY_BLOCKED_STEP: JourneyActionDefinition(
        code=LearningJourneyActionCode.RETRY_BLOCKED_STEP,
        allowed_statuses=frozenset({LearningJourneyStatus.LEARNING_BLOCKED, LearningJourneyStatus.CURRICULUM_UNRESOLVED}),
        source_capability="learning_journey.synchronization",
    ),
    LearningJourneyActionCode.PAUSE_JOURNEY: JourneyActionDefinition(
        code=LearningJourneyActionCode.PAUSE_JOURNEY,
        allowed_statuses=frozenset(status for status, _ in LearningJourneyStatus.choices if status not in TERMINAL_STATUSES and status != LearningJourneyStatus.PAUSED),
        source_capability="learning_journey.lifecycle",
    ),
    LearningJourneyActionCode.RESUME_JOURNEY: JourneyActionDefinition(
        code=LearningJourneyActionCode.RESUME_JOURNEY,
        allowed_statuses=frozenset({LearningJourneyStatus.PAUSED}),
        source_capability="learning_journey.lifecycle",
    ),
    LearningJourneyActionCode.WITHDRAW_JOURNEY: JourneyActionDefinition(
        code=LearningJourneyActionCode.WITHDRAW_JOURNEY,
        allowed_statuses=frozenset(status for status, _ in LearningJourneyStatus.choices if status not in TERMINAL_STATUSES),
        source_capability="learning_journey.lifecycle",
        requires_confirmation=True,
    ),
    LearningJourneyActionCode.SYNCHRONIZE: JourneyActionDefinition(
        code=LearningJourneyActionCode.SYNCHRONIZE,
        allowed_statuses=frozenset(status for status, _ in LearningJourneyStatus.choices if status not in {LearningJourneyStatus.WITHDRAWN, LearningJourneyStatus.ARCHIVED}),
        source_capability="learning_journey.synchronization",
    ),
}


def build_action(code: str, *, enabled: bool = True, disabled_reason: str = "", requires_confirmation: bool = False) -> AvailableAction:
    return AvailableAction(
        code=code,
        label=ACTION_COPY[code],
        endpoint_name=f"learning-journey-action-{code.lower().replace('_', '-')}",
        enabled=enabled,
        disabled_reason=disabled_reason,
        requires_confirmation=requires_confirmation,
    )


class SelfStudyJourneyActionPolicy:
    registry = SELF_STUDY_ACTIONS

    def definition(self, action_code: str) -> JourneyActionDefinition | None:
        return self.registry.get(action_code)

    def availability(self, *, journey: LearningJourney, action_code: str) -> tuple[bool, str]:
        definition = self.definition(action_code)
        if not definition:
            return False, "Journey action is not registered."
        if journey.journey_type != LearningJourneyType.SELF_STUDY:
            return False, "This action is only available for self-study journeys."
        if journey.status in TERMINAL_STATUSES:
            return False, "Terminal journeys cannot execute learning actions."
        if journey.status == LearningJourneyStatus.PAUSED and action_code != LearningJourneyActionCode.RESUME_JOURNEY:
            return False, "Paused journeys must be resumed before continuing."
        if journey.status not in definition.allowed_statuses:
            return False, "Journey action is not available for the current state."
        if not definition.implemented:
            return False, definition.unavailable_reason or "This action is not yet executable through the journey orchestrator."
        return True, ""

    def require_available(self, *, journey: LearningJourney, action_code: str) -> JourneyActionDefinition:
        definition = self.definition(action_code)
        if not definition:
            from django.core.exceptions import ValidationError

            raise ValidationError("Journey action is not registered.", code="LEARNING_JOURNEY_ACTION_NOT_REGISTERED")
        available, reason = self.availability(journey=journey, action_code=action_code)
        if not available:
            from django.core.exceptions import ValidationError

            raise ValidationError(reason, code="LEARNING_JOURNEY_ACTION_NOT_AVAILABLE")
        return definition

    def projected_action(self, *, journey: LearningJourney, action_code: str) -> AvailableAction:
        definition = self.definition(action_code)
        available, reason = self.availability(journey=journey, action_code=action_code)
        return build_action(
            action_code,
            enabled=available,
            disabled_reason=reason,
            requires_confirmation=definition.requires_confirmation if definition else False,
        )
