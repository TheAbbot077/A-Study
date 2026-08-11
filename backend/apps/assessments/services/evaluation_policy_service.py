from __future__ import annotations

from dataclasses import dataclass

from apps.assessments.domain.models import AssessmentPurpose


@dataclass(frozen=True)
class ResolvedEvaluationPolicy:
    policy_code: str
    policy_version: str
    automatic_evaluation_permitted: bool
    partial_correctness_permitted: bool
    human_review_required: bool
    disclosure_mode: str


class ResolveEvaluationPolicyService:
    POLICY_VERSION = "1"

    PURPOSE_POLICIES: dict[str, ResolvedEvaluationPolicy] = {
        AssessmentPurpose.PRACTICE: ResolvedEvaluationPolicy(
            policy_code="PRACTICE_STANDARD_EVALUATION",
            policy_version=POLICY_VERSION,
            automatic_evaluation_permitted=True,
            partial_correctness_permitted=True,
            human_review_required=False,
            disclosure_mode="CONTROLLED",
        ),
        AssessmentPurpose.CONCEPT_CHECK: ResolvedEvaluationPolicy(
            policy_code="CONCEPT_CHECK_STANDARD_EVALUATION",
            policy_version=POLICY_VERSION,
            automatic_evaluation_permitted=True,
            partial_correctness_permitted=False,
            human_review_required=False,
            disclosure_mode="RESTRICTED",
        ),
        AssessmentPurpose.ENTRY_DIAGNOSTIC: ResolvedEvaluationPolicy(
            policy_code="ENTRY_DIAGNOSTIC_STANDARD_EVALUATION",
            policy_version=POLICY_VERSION,
            automatic_evaluation_permitted=True,
            partial_correctness_permitted=False,
            human_review_required=False,
            disclosure_mode="PRIVATE",
        ),
    }

    DEFAULT_POLICY = ResolvedEvaluationPolicy(
        policy_code="DEFAULT_STANDARD_EVALUATION",
        policy_version=POLICY_VERSION,
        automatic_evaluation_permitted=True,
        partial_correctness_permitted=False,
        human_review_required=False,
        disclosure_mode="CONTROLLED",
    )

    def resolve(self, purpose: str) -> ResolvedEvaluationPolicy:
        return self.PURPOSE_POLICIES.get(purpose, self.DEFAULT_POLICY)
