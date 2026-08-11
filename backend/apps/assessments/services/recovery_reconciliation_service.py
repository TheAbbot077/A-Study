from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from apps.academic.domain.models import ContentConcept
from apps.assessments.domain.models import AssessmentExperience
from apps.assessments.services.mastery_interpretation_service import MasteryInterpretationService
from apps.assessments.services.pedagogical_response_service import PedagogicalResponseDecisionService
from apps.assessments.services.recovery_service import RecoveryObservationService


@dataclass(frozen=True)
class ReconciledRecoveryProjection:
    learner_id: str
    target_id: str
    recovery_status: str
    reconciliation_state: str
    current_mastery_state: str
    current_pedagogical_decision: str
    reason_code: str
    recovery: dict[str, Any]
    reconciled_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReconcileLearningRecoveryService:
    def __init__(
        self,
        recovery_service: RecoveryObservationService | None = None,
        mastery_interpretation_service: MasteryInterpretationService | None = None,
        pedagogical_response_service: PedagogicalResponseDecisionService | None = None,
    ) -> None:
        self.recovery_service = recovery_service or RecoveryObservationService()
        self.mastery_interpretation_service = mastery_interpretation_service or MasteryInterpretationService()
        self.pedagogical_response_service = pedagogical_response_service or PedagogicalResponseDecisionService()

    def reconcile(self, learner, content_concept: ContentConcept, *, source_experience: AssessmentExperience | None = None) -> ReconciledRecoveryProjection:
        recovery = self.recovery_service.project(learner, content_concept, source_experience=source_experience)
        mastery = self.mastery_interpretation_service.interpret(learner, content_concept)
        decision = self.pedagogical_response_service.decide(learner, content_concept)
        status, reconciliation_state, reason_code = self._resolve(recovery, mastery.state, decision.decision_code)
        return ReconciledRecoveryProjection(
            learner_id=str(learner.id),
            target_id=str(content_concept.id),
            recovery_status=status,
            reconciliation_state=reconciliation_state,
            current_mastery_state=mastery.state,
            current_pedagogical_decision=decision.decision_code,
            reason_code=reason_code,
            recovery=recovery.to_dict(),
            reconciled_at=mastery.updated_at,
        )

    def _resolve(self, recovery, mastery_state: str, decision_code: str) -> tuple[str, str, str]:
        if recovery.request.recovery_obsolete or mastery_state == "MASTERED":
            return "SUPERSEDED", "SUPERSEDED", "NEWER_MASTERY_AVAILABLE"
        if mastery_state == "INSUFFICIENT_EVIDENCE" and decision_code == "REQUEST_MORE_EVIDENCE":
            return "OPEN", "AWAITING_OBSERVATION", "EVIDENCE_STILL_INSUFFICIENT"
        if recovery.request.status == "READY":
            return "OPEN", "AWAITING_REASSESSMENT", "REASSESSMENT_ELIGIBLE"
        if recovery.request.status == "AWAITING_INTERPRETATION":
            return "OPEN", "AWAITING_PEDAGOGICAL_DECISION", "RECOVERY_PENDING"
        return "RESOLVED", "RESOLVED", "RECOVERY_CONCLUDED"
