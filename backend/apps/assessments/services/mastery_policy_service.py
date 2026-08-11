from __future__ import annotations

from dataclasses import dataclass

from apps.assessments.domain.models import AssessmentPurpose


@dataclass(frozen=True)
class ResolvedMasteryPolicy:
    policy_code: str
    policy_version: str
    minimum_evidence_count: int
    minimum_confidence: float
    mastery_threshold: float
    review_threshold: float


class ResolveMasteryPolicyService:
    POLICY_VERSION = "1"

    PURPOSE_POLICIES: dict[str, ResolvedMasteryPolicy] = {
        AssessmentPurpose.CONCEPT_CHECK: ResolvedMasteryPolicy(
            policy_code="CONCEPT_CHECK_MASTERY_POLICY",
            policy_version=POLICY_VERSION,
            minimum_evidence_count=1,
            minimum_confidence=0.7,
            mastery_threshold=0.8,
            review_threshold=0.5,
        ),
        AssessmentPurpose.ENTRY_DIAGNOSTIC: ResolvedMasteryPolicy(
            policy_code="ENTRY_DIAGNOSTIC_MASTERY_POLICY",
            policy_version=POLICY_VERSION,
            minimum_evidence_count=1,
            minimum_confidence=0.6,
            mastery_threshold=0.75,
            review_threshold=0.45,
        ),
        AssessmentPurpose.PRACTICE: ResolvedMasteryPolicy(
            policy_code="PRACTICE_MASTERY_POLICY",
            policy_version=POLICY_VERSION,
            minimum_evidence_count=1,
            minimum_confidence=0.5,
            mastery_threshold=0.7,
            review_threshold=0.4,
        ),
    }

    DEFAULT_POLICY = ResolvedMasteryPolicy(
        policy_code="DEFAULT_MASTERY_POLICY",
        policy_version=POLICY_VERSION,
        minimum_evidence_count=1,
        minimum_confidence=0.5,
        mastery_threshold=0.7,
        review_threshold=0.4,
    )

    def resolve(self, purpose: str) -> ResolvedMasteryPolicy:
        return self.PURPOSE_POLICIES.get(purpose, self.DEFAULT_POLICY)
