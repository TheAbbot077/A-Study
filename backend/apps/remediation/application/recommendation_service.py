from __future__ import annotations

from apps.assessments.domain.models import LearningEvidence
from apps.remediation.domain.services import RecommendationDraft, RecommendationPolicyRegistry


class RecommendationService:
    def __init__(self, policy_registry: RecommendationPolicyRegistry | None = None) -> None:
        self.policy_registry = policy_registry or RecommendationPolicyRegistry()

    def recommendations_for_evidence(self, evidence: LearningEvidence) -> list[RecommendationDraft]:
        return self.policy_registry.recommendations_for(evidence)
