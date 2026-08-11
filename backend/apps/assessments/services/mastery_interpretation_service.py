from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from apps.academic.domain.models import ContentConcept
from apps.assessments.domain.models import LearningEvidence, MasteryDecision, MasteryProfile
from apps.assessments.services.mastery_policy_service import ResolveMasteryPolicyService
from apps.assessments.services.mastery_service import MasteryService


@dataclass(frozen=True)
class MasteryInterpretationProjection:
    learner_id: str
    content_concept_id: str
    policy: dict[str, Any]
    evidence_count: int
    authoritative_evidence_ids: list[str]
    current_decision: str
    current_confidence: float
    state: str
    explanation: str
    previous_decision_id: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MasteryInterpretationService:
    def __init__(self, mastery_service: MasteryService | None = None) -> None:
        self.mastery_service = mastery_service or MasteryService()
        self.policy_service = ResolveMasteryPolicyService()

    def interpret(self, learner, content_concept: ContentConcept) -> MasteryInterpretationProjection:
        evidence = self.mastery_service.evidence_service.list_evidence_for_learner_concept(learner, content_concept)
        policy = self.policy_service.resolve(getattr(self._latest_evidence(evidence), "source_type", "") or "practice")
        decision = self._current_decision(learner, content_concept, evidence)
        profile = self._profile(learner, content_concept)
        state = self._state_for_decision(decision, evidence, profile)
        explanation = self._explanation(decision, evidence, policy)
        return MasteryInterpretationProjection(
            learner_id=str(learner.id),
            content_concept_id=str(content_concept.id),
            policy={
                "code": policy.policy_code,
                "version": policy.policy_version,
                "minimum_evidence_count": policy.minimum_evidence_count,
                "minimum_confidence": policy.minimum_confidence,
                "mastery_threshold": policy.mastery_threshold,
                "review_threshold": policy.review_threshold,
            },
            evidence_count=len(evidence),
            authoritative_evidence_ids=[str(item.id) for item in evidence],
            current_decision=decision.decision if decision else "not_enough_evidence",
            current_confidence=decision.confidence if decision else 0.0,
            state=state,
            explanation=explanation,
            previous_decision_id=str(profile.id) if profile else None,
            updated_at=str(profile.updated_at) if profile else None,
        )

    def _current_decision(self, learner, content_concept: ContentConcept, evidence: list[LearningEvidence]) -> MasteryDecision | None:
        if not evidence:
            return None
        try:
            return MasteryDecision.objects.filter(learner=learner, content_concept=content_concept).order_by("-created_at").first()
        except Exception:
            return None

    def _profile(self, learner, content_concept: ContentConcept) -> MasteryProfile | None:
        try:
            return MasteryProfile.objects.filter(learner=learner, content_concept=content_concept).first()
        except Exception:
            return None

    def _latest_evidence(self, evidence: list[LearningEvidence]) -> LearningEvidence | None:
        return evidence[0] if evidence else None

    def _state_for_decision(self, decision: MasteryDecision | None, evidence: list[LearningEvidence], profile: MasteryProfile | None) -> str:
        if not evidence:
            return "INSUFFICIENT_EVIDENCE"
        if profile and profile.current_decision == "mastered":
            return "MASTERED"
        if decision is None:
            return "UNDER_REVIEW"
        if decision.decision == "mastered":
            return "MASTERED"
        if decision.decision in {"needs_review", "not_mastered"}:
            return "UNDER_REVIEW"
        return "EMERGING"

    def _explanation(self, decision: MasteryDecision | None, evidence: list[LearningEvidence], policy) -> str:
        if not evidence:
            return "No authoritative evidence has been recorded yet."
        if decision is None:
            return "Evidence exists, but no persisted mastery decision is available."
        return decision.rationale or "Mastery is derived from the authoritative evidence set under the active policy."
