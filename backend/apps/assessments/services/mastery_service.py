from __future__ import annotations

from typing import Any, Optional

from apps.academic.domain.models import ContentConcept
from apps.core.exceptions import DomainValidationError
from apps.assessments.domain.models import (
    LearningEvidence,
    LearningEvidenceType,
    MasteryDecision,
    MasteryDecisionValue,
    MasteryProfile,
)
from apps.assessments.services.evidence_service import EvidenceService
from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import User


class MasteryService:
    POSITIVE_EVIDENCE_TYPES = {
        LearningEvidenceType.CORRECT_RESPONSE,
        LearningEvidenceType.EXPLANATION_QUALITY,
        LearningEvidenceType.APPLIED_REASONING,
        LearningEvidenceType.COMPLETION,
    }

    def __init__(
        self,
        event_publisher: Optional[EventPublisher] = None,
        evidence_service: Optional[EvidenceService] = None,
    ) -> None:
        self.event_publisher = event_publisher or EventPublisher()
        self.evidence_service = evidence_service or EvidenceService(event_publisher=self.event_publisher)

    def evaluate_mastery(self, learner: User, content_concept: ContentConcept) -> MasteryDecision:
        evidence = self.evidence_service.list_evidence_for_learner_concept(learner, content_concept)
        decision_value, confidence, rationale = self._derive_mastery_decision(evidence)
        decision = self.create_mastery_decision(
            learner=learner,
            content_concept=content_concept,
            decision=decision_value,
            confidence=confidence,
            evidence_count=len(evidence),
            rationale=rationale,
            metadata={"evidence_ids": [str(item.id) for item in evidence if getattr(item, "id", None)]},
        )
        self.update_mastery_profile(decision, evidence=evidence)
        return decision

    def create_mastery_decision(
        self,
        learner: User,
        content_concept: ContentConcept,
        decision: str,
        confidence: float,
        evidence_count: int,
        rationale: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> MasteryDecision:
        if decision not in MasteryDecisionValue.values:
            raise DomainValidationError(f"Unsupported mastery decision value: {decision}.")
        if not 0.0 <= confidence <= 1.0:
            raise DomainValidationError("Mastery decision confidence must be between 0 and 1.")

        mastery_decision = MasteryDecision.objects.create(
            learner=learner,
            content_concept=content_concept,
            decision=decision,
            confidence=confidence,
            evidence_count=evidence_count,
            rationale=rationale,
            metadata=metadata or {},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.mastery_decision_created",
                payload={
                    "mastery_decision_id": str(mastery_decision.id),
                    "learner_id": str(learner.id),
                    "content_concept_id": str(content_concept.id),
                    "decision": mastery_decision.decision,
                    "confidence": mastery_decision.confidence,
                    "evidence_count": mastery_decision.evidence_count,
                },
            )
        )
        return mastery_decision

    def update_mastery_profile(
        self,
        mastery_decision: MasteryDecision,
        evidence: Optional[list[LearningEvidence]] = None,
    ) -> MasteryProfile:
        last_evidence_at = self._latest_evidence_created_at(evidence or [])
        profile, _created = MasteryProfile.objects.update_or_create(
            learner=mastery_decision.learner,
            content_concept=mastery_decision.content_concept,
            defaults={
                "current_decision": mastery_decision.decision,
                "confidence": mastery_decision.confidence,
                "evidence_count": mastery_decision.evidence_count,
                "last_evidence_at": last_evidence_at,
            },
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.mastery_profile_updated",
                payload={
                    "mastery_profile_id": str(profile.id),
                    "learner_id": str(mastery_decision.learner.id),
                    "content_concept_id": str(mastery_decision.content_concept.id),
                    "current_decision": profile.current_decision,
                    "confidence": profile.confidence,
                    "evidence_count": profile.evidence_count,
                },
            )
        )
        return profile

    def get_mastery_profile(self, learner: User, content_concept: ContentConcept) -> MasteryProfile:
        return MasteryProfile.objects.get(learner=learner, content_concept=content_concept)

    def list_mastery_profiles_for_learner(self, learner: User) -> list[MasteryProfile]:
        return list(MasteryProfile.objects.filter(learner=learner).order_by("-updated_at"))

    def _derive_mastery_decision(self, evidence: list[LearningEvidence]) -> tuple[str, float, str]:
        if not evidence:
            return MasteryDecisionValue.NOT_ENOUGH_EVIDENCE, 0.0, "No learning evidence recorded for this concept."

        misconception_evidence = [item for item in evidence if item.evidence_type == LearningEvidenceType.MISCONCEPTION]
        positive_evidence = [item for item in evidence if item.evidence_type in self.POSITIVE_EVIDENCE_TYPES]
        partial_evidence = [item for item in evidence if item.evidence_type == LearningEvidenceType.PARTIAL_UNDERSTANDING]

        strong_misconception = [item for item in misconception_evidence if item.confidence >= 0.7]
        strong_positive = [
            item
            for item in positive_evidence
            if item.confidence >= 0.8 and (item.score is None or item.score >= 0.8)
        ]

        if strong_misconception and positive_evidence:
            return (
                MasteryDecisionValue.NEEDS_REVIEW,
                self._average_confidence(evidence),
                "Evidence includes both positive understanding and misconception signals.",
            )
        if strong_misconception:
            return (
                MasteryDecisionValue.NOT_MASTERED,
                max(item.confidence for item in strong_misconception),
                "High-confidence misconception evidence indicates the concept is not mastered.",
            )
        if strong_positive:
            return (
                MasteryDecisionValue.MASTERED,
                max(item.confidence for item in strong_positive),
                "High-confidence positive evidence indicates mastery for this concept.",
            )
        if misconception_evidence and (positive_evidence or partial_evidence):
            return (
                MasteryDecisionValue.NEEDS_REVIEW,
                self._average_confidence(evidence),
                "Mixed evidence requires review before a stronger mastery decision.",
            )
        return (
            MasteryDecisionValue.EMERGING,
            self._average_confidence(evidence),
            "Available evidence suggests emerging understanding but is not strong enough for mastery.",
        )

    def _average_confidence(self, evidence: list[LearningEvidence]) -> float:
        if not evidence:
            return 0.0
        return round(sum(item.confidence for item in evidence) / len(evidence), 4)

    def _latest_evidence_created_at(self, evidence: list[LearningEvidence]) -> Any:
        created_at_values = [item.created_at for item in evidence if getattr(item, "created_at", None)]
        if not created_at_values:
            return None
        return max(created_at_values)
