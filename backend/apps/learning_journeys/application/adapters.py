from __future__ import annotations

from dataclasses import dataclass

from apps.self_study.bridge_models import BridgePlanStatus
from apps.self_study.curriculum_models import (
    CandidateEligibility,
    CurriculumSubjectBindingStatus,
    MatchClassification,
    ResolutionAttemptStatus,
)
from apps.self_study.diagnostic_models import DiagnosticStatus
from apps.self_study.models import IntentStatus
from apps.self_study.onboarding_models import SelfStudyOnboardingStatus
from apps.self_study.orchestration_models import SelfStudyTeachingSessionState
from apps.self_study.teaching_models import TeachingPreparationManifestStatus
from apps.self_study.workspace_models import SelfStudyWorkspace, SelfStudyWorkspaceStatus

from ..domain.enums import (
    LearningJourneyActionCode,
    LearningJourneyBlockerCode,
    LearningJourneyStatus,
    LearningJourneyStatusReasonCode,
    LearningJourneyStepCode,
)
from ..domain.value_objects import AvailableAction, CurrentStep, JourneyBlocker, JourneyProjection, StatusReason
from .action_policy import build_action


STEP_COPY = {
    LearningJourneyStepCode.DISCOVER_GOAL: ("Tell Abbot what you want to study", "Start or continue a guided setup conversation.", 10),
    LearningJourneyStepCode.CONFIRM_INTENT: ("Confirm your learning goal", "Review the goal Abbot understood before it becomes the journey direction.", 20),
    LearningJourneyStepCode.RESOLVE_CURRICULUM: ("Find the right curriculum", "Abbot checks verified curriculum authority for your goal.", 30),
    LearningJourneyStepCode.SELECT_CURRICULUM: ("Choose a verified curriculum", "Select from backend-authorized curriculum options.", 40),
    LearningJourneyStepCode.WAIT_FOR_SUBJECT_BINDING: ("Wait for subject availability", "This verified curriculum is not yet available for self-study.", 50),
    LearningJourneyStepCode.COMPLETE_ENTRY_DIAGNOSTIC: ("Find your starting point", "Complete a short private diagnostic so Abbot can place you correctly.", 60),
    LearningJourneyStepCode.REVIEW_PLACEMENT: ("Review your placement", "Abbot is preparing your route from your starting point.", 70),
    LearningJourneyStepCode.COMPLETE_BRIDGE: ("Complete your bridge path", "Work through prerequisite steps before the target path.", 80),
    LearningJourneyStepCode.CREATE_LEARNING_PLAN: ("Build your study plan", "Abbot prepares the governed sequence for your goal.", 90),
    LearningJourneyStepCode.BEGIN_LEARNING: ("Begin learning", "Start a governed teaching session.", 100),
    LearningJourneyStepCode.CONTINUE_LEARNING: ("Continue learning", "Resume your current governed teaching session.", 110),
    LearningJourneyStepCode.RESOLVE_BLOCKER: ("Resolve the blocker", "A governed prerequisite must be fixed before continuing.", 120),
    LearningJourneyStepCode.REVIEW_PROGRESS: ("Review progress", "Review your evidence-backed progress.", 130),
    LearningJourneyStepCode.GOAL_COMPLETED: ("Learning goal completed", "This self-study goal is complete. This is not a qualification or credit award.", 140),
}


def step(code: str) -> CurrentStep:
    title, description, sequence = STEP_COPY[code]
    return CurrentStep(code=code, title=title, description=description, sequence=sequence)


def action(code: str, *, enabled: bool = True, disabled_reason: str = "", requires_confirmation: bool = False) -> AvailableAction:
    return build_action(code, enabled=enabled, disabled_reason=disabled_reason, requires_confirmation=requires_confirmation)


def blocker(
    code: str,
    *,
    category: str,
    message: str,
    capability: str,
    recoverable: bool = True,
    resolution_action_code: str = "",
) -> JourneyBlocker:
    return JourneyBlocker(
        code=code,
        category=category,
        message=message,
        recoverable=recoverable,
        blocking_capability=capability,
        resolution_action_code=resolution_action_code,
    )


@dataclass(frozen=True)
class SelfStudyJourneyAdapter:
    workspace: SelfStudyWorkspace

    def project(self) -> JourneyProjection:
        workspace = self.workspace
        refs = self._references()

        if workspace.status == SelfStudyWorkspaceStatus.ARCHIVED:
            return self._projection(
                LearningJourneyStatus.ARCHIVED,
                LearningJourneyStatusReasonCode.ARCHIVED_BY_POLICY,
                LearningJourneyStepCode.RESOLVE_BLOCKER,
                refs,
                blockers=(
                    blocker(
                        LearningJourneyBlockerCode.SOURCE_RECORD_MISSING,
                        category="workspace",
                        message="This workspace is archived.",
                        capability="self_study.workspace",
                        recoverable=False,
                    ),
                ),
            )

        onboarding = workspace.onboarding_sessions.order_by("-created_at").first()
        if not workspace.intent_id:
            if onboarding and onboarding.status == SelfStudyOnboardingStatus.AWAITING_CURRICULUM_SELECTION:
                return self._curriculum_selection_projection(onboarding, refs)
            if onboarding and onboarding.status == SelfStudyOnboardingStatus.RESOLVING_CURRICULUM:
                return self._projection(
                    LearningJourneyStatus.RESOLVING_CURRICULUM,
                    LearningJourneyStatusReasonCode.CURRICULUM_RESOLUTION_PENDING,
                    LearningJourneyStepCode.RESOLVE_CURRICULUM,
                    refs,
                )
            return self._projection(
                LearningJourneyStatus.DISCOVERING_GOAL,
                LearningJourneyStatusReasonCode.INTENT_NOT_CONFIRMED,
                LearningJourneyStepCode.DISCOVER_GOAL,
                refs,
                actions=(action(LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY),),
                blockers=(
                    blocker(
                        LearningJourneyBlockerCode.NO_CONFIRMED_INTENT,
                        category="intent",
                        message="A confirmed learning goal is required before Abbot can plan this journey.",
                        capability="self_study.onboarding",
                        resolution_action_code=LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY,
                    ),
                ),
            )

        intent = workspace.intent
        if intent.status == IntentStatus.DRAFT or intent.readiness_blockers():
            return self._projection(
                LearningJourneyStatus.DISCOVERING_GOAL,
                LearningJourneyStatusReasonCode.INTENT_NOT_CONFIRMED,
                LearningJourneyStepCode.CONFIRM_INTENT,
                refs,
                actions=(action(LearningJourneyActionCode.CONTINUE_GOAL_DISCOVERY),),
                blockers=(
                    blocker(
                        LearningJourneyBlockerCode.NO_CONFIRMED_INTENT,
                        category="intent",
                        message="Your learning goal is not confirmed yet.",
                        capability="self_study.intent",
                        resolution_action_code=LearningJourneyActionCode.CONTINUE_GOAL_DISCOVERY,
                    ),
                ),
            )

        if not workspace.curriculum_resolution_id and not intent.curriculum_selections.exists():
            return self._projection(
                LearningJourneyStatus.RESOLVING_CURRICULUM,
                LearningJourneyStatusReasonCode.CURRICULUM_RESOLUTION_PENDING,
                LearningJourneyStepCode.RESOLVE_CURRICULUM,
                refs,
                actions=(action(LearningJourneyActionCode.RETRY_CURRICULUM_RESOLUTION),),
            )

        if workspace.curriculum_resolution and workspace.curriculum_resolution.status == ResolutionAttemptStatus.FAILED:
            return self._projection(
                LearningJourneyStatus.CURRICULUM_UNRESOLVED,
                LearningJourneyStatusReasonCode.NO_GOVERNED_CURRICULUM,
                LearningJourneyStepCode.RESOLVE_CURRICULUM,
                refs,
                actions=(action(LearningJourneyActionCode.RETRY_CURRICULUM_RESOLUTION),),
                blockers=(
                    blocker(
                        LearningJourneyBlockerCode.NO_GOVERNED_CURRICULUM,
                        category="curriculum",
                        message="No governed curriculum has been confirmed for this learning goal yet.",
                        capability="self_study.curriculum_resolution",
                        resolution_action_code=LearningJourneyActionCode.RETRY_CURRICULUM_RESOLUTION,
                    ),
                ),
            )

        binding = self._active_self_study_binding()
        if not binding:
            if workspace.curriculum_resolution_id:
                return self._projection(
                    LearningJourneyStatus.SUBJECT_BINDING_UNAVAILABLE,
                    LearningJourneyStatusReasonCode.SELF_STUDY_BINDING_MISSING,
                    LearningJourneyStepCode.WAIT_FOR_SUBJECT_BINDING,
                    refs,
                    blockers=(
                        blocker(
                            LearningJourneyBlockerCode.SELF_STUDY_SUBJECT_BINDING_UNAVAILABLE,
                            category="subject_binding",
                            message="This verified curriculum is not yet available for self-study.",
                            capability="self_study.curriculum_subject_binding",
                            recoverable=False,
                        ),
                    ),
                    authority=self._authority_from_resolution(),
                )
            return self._projection(
                LearningJourneyStatus.SUBJECT_BINDING_REQUIRED,
                LearningJourneyStatusReasonCode.SELF_STUDY_BINDING_MISSING,
                LearningJourneyStepCode.WAIT_FOR_SUBJECT_BINDING,
                refs,
            )

        subject = {"id": str(binding.subject_id), "name": binding.subject.name}
        authority = {
            "type": "VERIFIED_CURRICULUM",
            "reference_id": str(binding.curriculum_version.curriculum_reference_id),
            "display_name": binding.curriculum_version.curriculum_reference.title,
        }

        diagnostic = workspace.active_diagnostic or intent.entry_diagnostics.order_by("-created_at").first()
        if not diagnostic:
            return self._projection(
                LearningJourneyStatus.STARTING_STATE_REQUIRED,
                LearningJourneyStatusReasonCode.DIAGNOSTIC_REQUIRED,
                LearningJourneyStepCode.COMPLETE_ENTRY_DIAGNOSTIC,
                refs,
                actions=(action(LearningJourneyActionCode.BEGIN_DIAGNOSTIC),),
                subject=subject,
                authority=authority,
            )
        if diagnostic.status in {DiagnosticStatus.READY, DiagnosticStatus.IN_PROGRESS}:
            return self._projection(
                LearningJourneyStatus.STARTING_STATE_IN_PROGRESS,
                LearningJourneyStatusReasonCode.DIAGNOSTIC_IN_PROGRESS,
                LearningJourneyStepCode.COMPLETE_ENTRY_DIAGNOSTIC,
                refs,
                actions=(action(LearningJourneyActionCode.CONTINUE_DIAGNOSTIC),),
                subject=subject,
                authority=authority,
            )
        if diagnostic.status not in {DiagnosticStatus.COMPLETED, DiagnosticStatus.SUPERSEDED}:
            return self._projection(
                LearningJourneyStatus.STARTING_STATE_REQUIRED,
                LearningJourneyStatusReasonCode.PLACEMENT_PENDING,
                LearningJourneyStepCode.REVIEW_PLACEMENT,
                refs,
                blockers=(
                    blocker(
                        LearningJourneyBlockerCode.PLACEMENT_NOT_CONFIRMED,
                        category="diagnostic",
                        message="Placement is not confirmed yet.",
                        capability="self_study.entry_diagnostic",
                    ),
                ),
                subject=subject,
                authority=authority,
            )

        bridge_plan = workspace.active_bridge_plan or intent.bridge_plans.order_by("-created_at").first()
        if not bridge_plan:
            return self._projection(
                LearningJourneyStatus.PLAN_REQUIRED,
                LearningJourneyStatusReasonCode.LEARNING_PLAN_REQUIRED,
                LearningJourneyStepCode.CREATE_LEARNING_PLAN,
                refs,
                actions=(
                    action(
                        LearningJourneyActionCode.GENERATE_LEARNING_PLAN,
                        enabled=False,
                        disabled_reason="Learning plan generation is represented by the existing bridge-plan and teaching-readiness capabilities.",
                    ),
                ),
                subject=subject,
                authority=authority,
            )
        if bridge_plan.status in {BridgePlanStatus.BLOCKED, BridgePlanStatus.STALE, BridgePlanStatus.INVALIDATED}:
            return self._projection(
                LearningJourneyStatus.LEARNING_BLOCKED,
                LearningJourneyStatusReasonCode.BRIDGE_PLAN_REQUIRED,
                LearningJourneyStepCode.RESOLVE_BLOCKER,
                refs,
                blockers=(
                    blocker(
                        LearningJourneyBlockerCode.BRIDGE_PLAN_NOT_READY,
                        category="plan",
                        message="The bridge plan is not ready.",
                        capability="self_study.bridge_plan",
                        resolution_action_code=LearningJourneyActionCode.RETRY_BLOCKED_STEP,
                    ),
                ),
                subject=subject,
                authority=authority,
            )
        if bridge_plan.status not in {BridgePlanStatus.APPROVED, BridgePlanStatus.ACTIVE}:
            return self._projection(
                LearningJourneyStatus.BRIDGE_REQUIRED,
                LearningJourneyStatusReasonCode.BRIDGE_PLAN_REQUIRED,
                LearningJourneyStepCode.COMPLETE_BRIDGE,
                refs,
                actions=(
                    action(
                        LearningJourneyActionCode.GENERATE_BRIDGE_PLAN,
                        enabled=False,
                        disabled_reason="Bridge generation requires explicit target nodes from the bridge planning capability.",
                    ),
                ),
                subject=subject,
                authority=authority,
            )

        preparation = workspace.active_teaching_preparation or intent.teaching_preparation_manifests.order_by("-created_at").first()
        if not preparation:
            return self._projection(
                LearningJourneyStatus.PLAN_READY,
                LearningJourneyStatusReasonCode.LEARNING_PLAN_REQUIRED,
                LearningJourneyStepCode.BEGIN_LEARNING,
                refs,
                actions=(
                    action(
                        LearningJourneyActionCode.ACTIVATE_LEARNING_PLAN,
                        enabled=False,
                        disabled_reason="Plan activation remains owned by the authoritative plan and teaching readiness capability.",
                    ),
                ),
                subject=subject,
                authority=authority,
            )
        if preparation.status not in {TeachingPreparationManifestStatus.READY, TeachingPreparationManifestStatus.PUBLISHED}:
            return self._projection(
                LearningJourneyStatus.LEARNING_BLOCKED,
                LearningJourneyStatusReasonCode.TEACHING_NOT_READY,
                LearningJourneyStepCode.RESOLVE_BLOCKER,
                refs,
                blockers=(
                    blocker(
                        LearningJourneyBlockerCode.TEACHING_CONTENT_NOT_READY,
                        category="teaching",
                        message="Teaching content is not ready yet.",
                        capability="self_study.teaching_preparation",
                        resolution_action_code=LearningJourneyActionCode.RETRY_BLOCKED_STEP,
                    ),
                ),
                subject=subject,
                authority=authority,
            )

        session = workspace.active_teaching_session or intent.teaching_sessions.order_by("-created_at").first()
        if session and session.state == SelfStudyTeachingSessionState.COMPLETED:
            return self._projection(
                LearningJourneyStatus.LEARNING_GOAL_COMPLETED,
                LearningJourneyStatusReasonCode.GOAL_COMPLETED,
                LearningJourneyStepCode.GOAL_COMPLETED,
                refs,
                subject=subject,
                authority=authority,
            )
        if session:
            return self._projection(
                LearningJourneyStatus.LEARNING_ACTIVE,
                LearningJourneyStatusReasonCode.LEARNING_PLAN_REQUIRED,
                LearningJourneyStepCode.CONTINUE_LEARNING,
                refs,
            actions=(
                action(
                    LearningJourneyActionCode.CONTINUE_TEACHING_SESSION,
                    enabled=False,
                    disabled_reason="Teaching turn continuation remains owned by the teaching orchestration service.",
                ),
            ),
                subject=subject,
                authority=authority,
            )
        return self._projection(
            LearningJourneyStatus.LEARNING_ACTIVE,
            LearningJourneyStatusReasonCode.LEARNING_PLAN_REQUIRED,
            LearningJourneyStepCode.BEGIN_LEARNING,
            refs,
            actions=(
                action(
                    LearningJourneyActionCode.BEGIN_TEACHING_SESSION,
                    enabled=False,
                    disabled_reason="Teaching session creation remains owned by the teaching orchestration service.",
                ),
            ),
            subject=subject,
            authority=authority,
        )

    def _curriculum_selection_projection(self, onboarding, refs: dict) -> JourneyProjection:
        candidates = list(onboarding.active_resolution_attempt.candidates.all()) if onboarding.active_resolution_attempt_id else []
        eligible = [
            candidate
            for candidate in candidates
            if candidate.eligibility == CandidateEligibility.ELIGIBLE
            and candidate.match_classification in {MatchClassification.EXACT, MatchClassification.STRONG}
        ]
        if not candidates:
            return self._projection(
                LearningJourneyStatus.CURRICULUM_UNRESOLVED,
                LearningJourneyStatusReasonCode.NO_GOVERNED_CURRICULUM,
                LearningJourneyStepCode.RESOLVE_CURRICULUM,
                refs,
                actions=(action(LearningJourneyActionCode.RETRY_CURRICULUM_RESOLUTION),),
                blockers=(
                    blocker(
                        LearningJourneyBlockerCode.NO_GOVERNED_CURRICULUM,
                        category="curriculum",
                        message="No governed curriculum has been confirmed for this learning goal yet.",
                        capability="self_study.curriculum_resolution",
                        resolution_action_code=LearningJourneyActionCode.RETRY_CURRICULUM_RESOLUTION,
                    ),
                ),
            )
        if not eligible:
            return self._projection(
                LearningJourneyStatus.SUBJECT_BINDING_UNAVAILABLE,
                LearningJourneyStatusReasonCode.SELF_STUDY_BINDING_MISSING,
                LearningJourneyStepCode.WAIT_FOR_SUBJECT_BINDING,
                refs,
                blockers=(
                    blocker(
                        LearningJourneyBlockerCode.SELF_STUDY_SUBJECT_BINDING_UNAVAILABLE,
                        category="subject_binding",
                        message="This verified curriculum is not yet available for self-study.",
                        capability="self_study.curriculum_subject_binding",
                        recoverable=False,
                    ),
                ),
            )
        return self._projection(
            LearningJourneyStatus.CURRICULUM_MATCHED,
            LearningJourneyStatusReasonCode.CURRICULUM_SELECTION_REQUIRED,
            LearningJourneyStepCode.SELECT_CURRICULUM,
            refs,
            actions=(action(LearningJourneyActionCode.SELECT_CURRICULUM),),
            blockers=(
                blocker(
                    LearningJourneyBlockerCode.CURRICULUM_SELECTION_REQUIRED,
                    category="curriculum",
                    message="A verified curriculum selection is required before the journey can continue.",
                    capability="self_study.curriculum_resolution",
                    resolution_action_code=LearningJourneyActionCode.SELECT_CURRICULUM,
                ),
            ),
        )

    def _projection(
        self,
        status: str,
        reason_code: str,
        step_code: str,
        refs: dict,
        *,
        actions: tuple[AvailableAction, ...] = (),
        blockers: tuple[JourneyBlocker, ...] = (),
        subject: dict | None = None,
        authority: dict | None = None,
    ) -> JourneyProjection:
        return JourneyProjection(
            status=status,
            status_reason=StatusReason(code=reason_code),
            current_step=step(step_code),
            available_actions=actions + (action(LearningJourneyActionCode.SYNCHRONIZE),),
            blockers=blockers,
            capability_references=refs,
            subject=subject,
            authority=authority,
        )

    def _references(self) -> dict:
        workspace = self.workspace
        intent = workspace.intent
        diagnostic = workspace.active_diagnostic or (intent.entry_diagnostics.order_by("-created_at").first() if intent else None)
        bridge_plan = workspace.active_bridge_plan or (intent.bridge_plans.order_by("-created_at").first() if intent else None)
        preparation = workspace.active_teaching_preparation or (
            intent.teaching_preparation_manifests.order_by("-created_at").first() if intent else None
        )
        session = workspace.active_teaching_session or (intent.teaching_sessions.order_by("-created_at").first() if intent else None)
        return {
            "self_study_workspace_id": str(workspace.id),
            "intent_id": str(workspace.intent_id) if workspace.intent_id else "",
            "curriculum_resolution_attempt_id": str(workspace.curriculum_resolution_id) if workspace.curriculum_resolution_id else "",
            "diagnostic_id": str(diagnostic.id) if diagnostic else "",
            "bridge_plan_id": str(bridge_plan.id) if bridge_plan else "",
            "learning_plan_id": str(bridge_plan.id) if bridge_plan else "",
            "teaching_preparation_id": str(preparation.id) if preparation else "",
            "active_teaching_session_id": str(session.id) if session else "",
        }

    def _active_self_study_binding(self):
        if self.workspace.intent_id and self.workspace.intent.subject_id and self.workspace.curriculum_resolution_id:
            selection = self.workspace.intent.curriculum_selections.select_related("curriculum_version__curriculum_reference").first()
            if selection:
                return (
                    selection.curriculum_version.subject_bindings.select_related("subject", "curriculum_version__curriculum_reference")
                    .filter(subject_id=self.workspace.intent.subject_id, status=CurriculumSubjectBindingStatus.ACTIVE)
                    .first()
                )
        return None

    def _authority_from_resolution(self) -> dict | None:
        if not self.workspace.curriculum_resolution_id:
            return None
        candidate = self.workspace.curriculum_resolution.candidates.select_related("curriculum_version__curriculum_reference").first()
        if not candidate:
            return None
        return {
            "type": "VERIFIED_CURRICULUM",
            "reference_id": str(candidate.curriculum_version.curriculum_reference_id),
            "display_name": candidate.curriculum_version.curriculum_reference.title,
        }


class InstitutionalJourneyAdapter:
    def project(self) -> JourneyProjection:
        return JourneyProjection(
            status=LearningJourneyStatus.SUBJECT_BINDING_REQUIRED,
            status_reason=StatusReason(code=LearningJourneyStatusReasonCode.INSTITUTIONAL_ASSIGNMENT_REQUIRED),
            current_step=step(LearningJourneyStepCode.WAIT_FOR_SUBJECT_BINDING),
            available_actions=(action(LearningJourneyActionCode.SYNCHRONIZE),),
            blockers=(
                blocker(
                    LearningJourneyBlockerCode.INSTITUTIONAL_ASSIGNMENT_REQUIRED,
                    category="institutional_authority",
                    message="Institutional assignment is required before this journey can continue.",
                    capability="institutions.assignment",
                    recoverable=False,
                ),
            ),
            capability_references={},
        )
