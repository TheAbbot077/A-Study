from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from apps.academic.domain.models import ContentConcept
from apps.assessments.domain.models import AssessmentExperience, AssessmentPurpose
from apps.assessments.services.mastery_interpretation_service import MasteryInterpretationService
from apps.assessments.services.pedagogical_response_service import PedagogicalResponseDecisionService
from apps.remediation.domain.models import RemediationPlan, RemediationPlanStatus


@dataclass(frozen=True)
class RecoveryObservationRequestProjection:
    learner_id: str
    target_id: str
    origin_target_id: str
    pedagogical_decision_id: str | None
    recovery_reason: str
    policy: dict[str, Any]
    cycle_number: int
    status: str
    mastery_state: str
    remediation_plan_id: str | None = None
    learning_journey_id: str | None = None
    recovery_obsolete: bool = False
    next_action: str = "WAIT_FOR_RECOVERY_DECISION"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReassessmentBlueprintProjection:
    target_id: str
    assessment_purpose: str
    recovery_reason: str
    required_evidence_role: str
    item_reuse_policy: str
    prior_item_ids: list[str]
    prior_exposure_count: int
    assessment_environment_reference: dict[str, Any]
    policy: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecoveryProjection:
    request: RecoveryObservationRequestProjection
    blueprint: ReassessmentBlueprintProjection

    def to_dict(self) -> dict[str, Any]:
        return {"request": self.request.to_dict(), "blueprint": self.blueprint.to_dict()}


class RecoveryObservationService:
    POLICY_CODE = "recovery.observation"
    POLICY_VERSION = "1"

    def __init__(
        self,
        mastery_interpretation_service: MasteryInterpretationService | None = None,
        pedagogical_response_service: PedagogicalResponseDecisionService | None = None,
    ) -> None:
        self.mastery_interpretation_service = mastery_interpretation_service or MasteryInterpretationService()
        self.pedagogical_response_service = pedagogical_response_service or PedagogicalResponseDecisionService()

    def project(self, learner, content_concept: ContentConcept, *, source_experience: AssessmentExperience | None = None) -> RecoveryProjection:
        mastery = self.mastery_interpretation_service.interpret(learner, content_concept)
        decision = self.pedagogical_response_service.decide(learner, content_concept)
        remediation_plan = self._active_remediation_plan(learner, content_concept)
        recovery_reason = self._recovery_reason(mastery.state, decision.decision_code, remediation_plan)
        cycle_number = self._cycle_number(learner, content_concept, source_experience)
        request = RecoveryObservationRequestProjection(
            learner_id=str(learner.id),
            target_id=str(content_concept.id),
            origin_target_id=str(getattr(source_experience, "content_concept_id", content_concept.id)),
            pedagogical_decision_id=str(getattr(source_experience, "id", "")) if source_experience else None,
            recovery_reason=recovery_reason,
            policy={
                "code": self.POLICY_CODE,
                "version": self.POLICY_VERSION,
                "mastery_state": mastery.state,
                "decision_code": decision.decision_code,
            },
            cycle_number=cycle_number,
            status="READY" if self._is_ready(mastery.state, decision.decision_code, remediation_plan) else "AWAITING_INTERPRETATION",
            mastery_state=mastery.state,
            remediation_plan_id=str(remediation_plan.id) if remediation_plan is not None else None,
            learning_journey_id=str(getattr(source_experience, "learning_journey_id", "")) if source_experience and source_experience.learning_journey_id else None,
            recovery_obsolete=False,
            next_action=self._next_action(mastery.state, decision.decision_code, remediation_plan),
        )
        blueprint = ReassessmentBlueprintProjection(
            target_id=str(content_concept.id),
            assessment_purpose=AssessmentPurpose.REMEDIATION_CHECK,
            recovery_reason=recovery_reason,
            required_evidence_role="fresh_observation",
            item_reuse_policy=self._item_reuse_policy(mastery.state, decision.decision_code, remediation_plan),
            prior_item_ids=self._prior_item_ids(learner, content_concept),
            prior_exposure_count=len(self._prior_item_ids(learner, content_concept)),
            assessment_environment_reference={
                "code": "assessment.environment.recovery",
                "version": self.POLICY_VERSION,
            },
            policy={
                "code": self.POLICY_CODE,
                "version": self.POLICY_VERSION,
            },
        )
        return RecoveryProjection(request=request, blueprint=blueprint)

    def _recovery_reason(self, mastery_state: str, decision_code: str, remediation_plan: RemediationPlan | None) -> str:
        if mastery_state == "INSUFFICIENT_EVIDENCE" or decision_code == "REQUEST_MORE_EVIDENCE":
            return "INSUFFICIENT_EVIDENCE"
        if remediation_plan is not None and remediation_plan.status in {RemediationPlanStatus.COMPLETED, RemediationPlanStatus.CLOSED}:
            return "POST_REMEDIATION"
        if decision_code == "REQUEST_REASSESSMENT":
            return "POST_GUIDED_PRACTICE"
        if decision_code == "INITIATE_TARGETED_REMEDIATION":
            return "POST_REMEDIATION"
        return "AUTHORIZED_MANUAL_REASSESSMENT"

    def _is_ready(self, mastery_state: str, decision_code: str, remediation_plan: RemediationPlan | None) -> bool:
        if mastery_state == "INSUFFICIENT_EVIDENCE":
            return True
        if remediation_plan is not None and remediation_plan.status in {RemediationPlanStatus.COMPLETED, RemediationPlanStatus.CLOSED}:
            return True
        return decision_code in {"REQUEST_REASSESSMENT", "REQUEST_MORE_EVIDENCE"}

    def _next_action(self, mastery_state: str, decision_code: str, remediation_plan: RemediationPlan | None) -> str:
        if self._is_ready(mastery_state, decision_code, remediation_plan):
            return "START_REASSESSMENT"
        if remediation_plan is not None and remediation_plan.status in {RemediationPlanStatus.PENDING, RemediationPlanStatus.ACTIVE, RemediationPlanStatus.ESCALATED}:
            return "WAIT_FOR_INTERPRETATION"
        return "WAIT_FOR_RECOVERY_DECISION"

    def _item_reuse_policy(self, mastery_state: str, decision_code: str, remediation_plan: RemediationPlan | None) -> str:
        if mastery_state == "INSUFFICIENT_EVIDENCE":
            return "REQUIRE_NEW_ITEMS"
        if remediation_plan is not None and remediation_plan.status in {RemediationPlanStatus.COMPLETED, RemediationPlanStatus.CLOSED}:
            return "ALLOW_IF_POOL_EXHAUSTED"
        if decision_code == "REQUEST_REASSESSMENT":
            return "AVOID_PREVIOUS_ITEMS"
        return "ALLOW_REUSE"

    def _cycle_number(self, learner, content_concept: ContentConcept, source_experience: AssessmentExperience | None) -> int:
        queryset = AssessmentExperience.objects.filter(learner=learner, content_concept=content_concept)
        if source_experience is not None and getattr(source_experience, "id", None):
            queryset = queryset.filter(created_at__gte=source_experience.created_at)
        return max(1, queryset.count())

    def _prior_item_ids(self, learner, content_concept: ContentConcept) -> list[str]:
        item_ids: list[str] = []
        for experience in AssessmentExperience.objects.filter(learner=learner, content_concept=content_concept).select_related("assessment_attempt"):
            attempt = getattr(experience, "assessment_attempt", None)
            if attempt is None:
                continue
            for response in attempt.responses.all():
                item_ids.append(str(response.item_id))
        return item_ids

    def _active_remediation_plan(self, learner, content_concept: ContentConcept) -> RemediationPlan | None:
        return (
            RemediationPlan.objects.filter(
                learner=learner,
                content_concept=content_concept,
                status__in=[RemediationPlanStatus.PENDING, RemediationPlanStatus.ACTIVE, RemediationPlanStatus.ESCALATED],
            )
            .order_by("-created_at")
            .first()
        )
