from __future__ import annotations

from typing import Any, Optional

from apps.academic.domain.models import ContentConcept
from apps.assessments.domain.models import LearningEvidence, LearningEvidenceSourceType, LearningEvidenceType
from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import User


class EvidenceService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def record_evidence(
        self,
        learner: User,
        content_concept: ContentConcept,
        source_type: str,
        source_id: str,
        evidence_type: str,
        score: Optional[float] = None,
        confidence: float = 0.0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> LearningEvidence:
        self._validate_evidence(source_type, evidence_type, score, confidence)

        evidence = LearningEvidence.objects.create(
            learner=learner,
            content_concept=content_concept,
            source_type=source_type,
            source_id=str(source_id),
            evidence_type=evidence_type,
            score=score,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "assessment.learning_evidence_recorded",
                payload={
                    "learning_evidence_id": str(evidence.id),
                    "learner_id": str(learner.id),
                    "content_concept_id": str(content_concept.id),
                    "source_type": evidence.source_type,
                    "source_id": evidence.source_id,
                    "evidence_type": evidence.evidence_type,
                    "confidence": evidence.confidence,
                },
            )
        )
        return evidence

    def list_evidence_for_learner(self, learner: User) -> list[LearningEvidence]:
        return list(LearningEvidence.objects.filter(learner=learner).order_by("-created_at"))

    def list_evidence_for_concept(self, content_concept: ContentConcept) -> list[LearningEvidence]:
        return list(LearningEvidence.objects.filter(content_concept=content_concept).order_by("-created_at"))

    def list_evidence_for_learner_concept(
        self,
        learner: User,
        content_concept: ContentConcept,
    ) -> list[LearningEvidence]:
        return list(
            LearningEvidence.objects.filter(learner=learner, content_concept=content_concept).order_by("-created_at")
        )

    def _validate_evidence(
        self,
        source_type: str,
        evidence_type: str,
        score: Optional[float],
        confidence: float,
    ) -> None:
        if source_type not in LearningEvidenceSourceType.values:
            raise ValueError(f"Unsupported learning evidence source type: {source_type}.")
        if evidence_type not in LearningEvidenceType.values:
            raise ValueError(f"Unsupported learning evidence type: {evidence_type}.")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Learning evidence confidence must be between 0 and 1.")
        if score is not None and not 0.0 <= score <= 1.0:
            raise ValueError("Learning evidence score must be null or between 0 and 1.")
