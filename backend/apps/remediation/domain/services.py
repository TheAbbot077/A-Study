from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from apps.assessments.domain.models import LearningEvidence, LearningEvidenceType
from apps.remediation.domain.models import RemediationRecommendationType


@dataclass(frozen=True)
class RecommendationDraft:
    recommendation_type: str
    title: str
    rationale: str
    priority: int = 1
    metadata: dict = field(default_factory=dict)


class RecommendationPolicy(Protocol):
    def supports(self, evidence: LearningEvidence) -> bool: ...
    def recommend(self, evidence: LearningEvidence) -> list[RecommendationDraft]: ...


class MisconceptionPolicy:
    def supports(self, evidence: LearningEvidence) -> bool:
        return evidence.evidence_type == LearningEvidenceType.MISCONCEPTION

    def recommend(self, evidence: LearningEvidence) -> list[RecommendationDraft]:
        return [
            RecommendationDraft(
                recommendation_type=RemediationRecommendationType.REVIEW_LESSON,
                title="Review the source lesson",
                rationale="Misconception evidence indicates the learner should revisit the grounded source material.",
                priority=1,
            ),
            RecommendationDraft(
                recommendation_type=RemediationRecommendationType.EDUCATOR_REVIEW,
                title="Escalate misconception for educator review",
                rationale="A misconception may require human review if it persists after remediation.",
                priority=2,
            ),
        ]


class PartialUnderstandingPolicy:
    def supports(self, evidence: LearningEvidence) -> bool:
        return evidence.evidence_type == LearningEvidenceType.PARTIAL_UNDERSTANDING

    def recommend(self, evidence: LearningEvidence) -> list[RecommendationDraft]:
        return [
            RecommendationDraft(
                recommendation_type=RemediationRecommendationType.REPEAT_ACTIVITY,
                title="Repeat a focused practice activity",
                rationale="Partial understanding evidence suggests targeted practice before re-evaluation.",
                priority=1,
            ),
            RecommendationDraft(
                recommendation_type=RemediationRecommendationType.ADDITIONAL_QUESTIONS,
                title="Answer additional concept questions",
                rationale="Additional questions can expose whether the partial understanding is stable.",
                priority=2,
            ),
        ]


class LowConfidencePolicy:
    def supports(self, evidence: LearningEvidence) -> bool:
        return evidence.confidence < 0.5

    def recommend(self, evidence: LearningEvidence) -> list[RecommendationDraft]:
        return [
            RecommendationDraft(
                recommendation_type=RemediationRecommendationType.READ_SOURCE_MATERIAL,
                title="Read supporting source material",
                rationale="Low-confidence evidence should be strengthened with source review.",
                priority=3,
            )
        ]


class RecommendationPolicyRegistry:
    def __init__(self, policies: list[RecommendationPolicy] | None = None) -> None:
        self._policies = policies or [MisconceptionPolicy(), PartialUnderstandingPolicy(), LowConfidencePolicy()]

    def register(self, policy: RecommendationPolicy) -> None:
        self._policies.append(policy)

    def recommendations_for(self, evidence: LearningEvidence) -> list[RecommendationDraft]:
        drafts: list[RecommendationDraft] = []
        for policy in self._policies:
            if policy.supports(evidence):
                drafts.extend(policy.recommend(evidence))
        return drafts


__all__ = [
    "RecommendationDraft",
    "RecommendationPolicy",
    "MisconceptionPolicy",
    "PartialUnderstandingPolicy",
    "LowConfidencePolicy",
    "RecommendationPolicyRegistry",
]
