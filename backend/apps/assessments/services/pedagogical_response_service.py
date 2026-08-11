from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from apps.academic.domain.models import ContentConcept
from apps.assessments.domain.models import LearningEvidence, MasteryDecisionValue, MasteryProfile
from apps.assessments.services.mastery_interpretation_service import MasteryInterpretationService
from apps.remediation.application import RemediationPlanningService


@dataclass(frozen=True)
class PedagogicalResponseDecision:
    learner_id: str
    content_concept_id: str
    mastery_state: str
    decision_code: str
    decision_version: str
    justification: str
    requires_remediation: bool
    remediation_plan_id: str | None = None
    evidence_count: int = 0
    authoritative_evidence_ids: list[str] = None
    previous_decision: str | None = None
    decision_state: str = "DETERMINISTIC"
    decided_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["authoritative_evidence_ids"] is None:
            data["authoritative_evidence_ids"] = []
        return data


class PedagogicalResponseDecisionService:
    DECISION_VERSION = "1"

    def __init__(
        self,
        mastery_interpretation_service: MasteryInterpretationService | None = None,
        remediation_planning_service: RemediationPlanningService | None = None,
    ) -> None:
        self.mastery_interpretation_service = mastery_interpretation_service or MasteryInterpretationService()
        self.remediation_planning_service = remediation_planning_service or RemediationPlanningService()

    def decide(self, learner, content_concept: ContentConcept) -> PedagogicalResponseDecision:
        mastery = self.mastery_interpretation_service.interpret(learner, content_concept)
        evidence = self._evidence_for(learner, content_concept)

        if mastery.state == "INSUFFICIENT_EVIDENCE":
            return self._decision(
                learner=learner,
                content_concept=content_concept,
                mastery_state=mastery.state,
                decision_code="REQUEST_MORE_EVIDENCE",
                justification="The current evidence set is not sufficient for a stronger pedagogical response.",
                requires_remediation=False,
                evidence=evidence,
                previous_decision=mastery.current_decision,
            )

        if mastery.state == "MASTERED":
            return self._decision(
                learner=learner,
                content_concept=content_concept,
                mastery_state=mastery.state,
                decision_code="DO_NOTHING",
                justification="The authoritative evidence set already supports mastery.",
                requires_remediation=False,
                evidence=evidence,
                previous_decision=mastery.current_decision,
            )

        if mastery.current_decision in {MasteryDecisionValue.NOT_MASTERED, MasteryDecisionValue.NEEDS_REVIEW}:
            plan = self._active_remediation_plan(learner, content_concept)
            if plan is None and evidence:
                plan = self.remediation_planning_service.plan_from_evidence(evidence[0])
            if plan is not None:
                return self._decision(
                    learner=learner,
                    content_concept=content_concept,
                    mastery_state=mastery.state,
                    decision_code="INITIATE_TARGETED_REMEDIATION",
                    justification="The authoritative mastery interpretation supports targeted remediation.",
                    requires_remediation=True,
                    remediation_plan_id=str(plan.id),
                    evidence=evidence,
                    previous_decision=mastery.current_decision,
                )
            return self._decision(
                learner=learner,
                content_concept=content_concept,
                mastery_state=mastery.state,
                decision_code="REQUEST_REASSESSMENT",
                justification="The learner needs more governed evidence before remediation can be justified.",
                requires_remediation=False,
                evidence=evidence,
                previous_decision=mastery.current_decision,
            )

        return self._decision(
            learner=learner,
            content_concept=content_concept,
            mastery_state=mastery.state,
            decision_code="CONTINUE_INSTRUCTION",
            justification="The mastery interpretation does not justify a stronger intervention yet.",
            requires_remediation=False,
            evidence=evidence,
            previous_decision=mastery.current_decision,
        )

    def _decision(
        self,
        *,
        learner,
        content_concept: ContentConcept,
        mastery_state: str,
        decision_code: str,
        justification: str,
        requires_remediation: bool,
        evidence: list[LearningEvidence],
        previous_decision: str | None,
        remediation_plan_id: str | None = None,
    ) -> PedagogicalResponseDecision:
        return PedagogicalResponseDecision(
            learner_id=str(learner.id),
            content_concept_id=str(content_concept.id),
            mastery_state=mastery_state,
            decision_code=decision_code,
            decision_version=self.DECISION_VERSION,
            justification=justification,
            requires_remediation=requires_remediation,
            remediation_plan_id=remediation_plan_id,
            evidence_count=len(evidence),
            authoritative_evidence_ids=[str(item.id) for item in evidence],
            previous_decision=previous_decision,
            decided_at=None,
        )

    def _evidence_for(self, learner, content_concept: ContentConcept) -> list[LearningEvidence]:
        return list(LearningEvidence.objects.filter(learner=learner, content_concept=content_concept).order_by("-created_at"))

    def _active_remediation_plan(self, learner, content_concept: ContentConcept):
        from apps.remediation.domain.models import RemediationPlan, RemediationPlanStatus

        return (
            RemediationPlan.objects.filter(
                learner=learner,
                content_concept=content_concept,
                status__in=[RemediationPlanStatus.PENDING, RemediationPlanStatus.ACTIVE, RemediationPlanStatus.ESCALATED],
            )
            .order_by("-created_at")
            .first()
        )
