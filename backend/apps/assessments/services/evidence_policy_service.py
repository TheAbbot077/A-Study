from __future__ import annotations

from dataclasses import dataclass

from apps.assessments.domain.models import AssessmentPurpose, AssessmentEvaluation, AssessmentEvaluationOutcome


@dataclass(frozen=True)
class ResolvedEvidencePolicy:
    policy_code: str
    policy_version: str
    can_create_evidence: bool
    evidence_polarity: str
    reason_code: str | None = None


class ResolveEvaluationEvidencePolicyService:
    POLICY_VERSION = "1"

    def resolve(self, evaluation: AssessmentEvaluation) -> ResolvedEvidencePolicy:
        purpose = getattr(evaluation.response.attempt.assessment, "purpose", AssessmentPurpose.PRACTICE)
        has_new_lifecycle = hasattr(evaluation, "status") or hasattr(evaluation, "outcome")
        if has_new_lifecycle and getattr(evaluation, "status", "completed") != "completed":
            return ResolvedEvidencePolicy(
                policy_code=f"{purpose.upper()}_EVIDENCE_POLICY",
                policy_version=self.POLICY_VERSION,
                can_create_evidence=False,
                evidence_polarity="NONE",
                reason_code="EVALUATION_NOT_COMPLETED",
            )
        if not has_new_lifecycle:
            outcome = self._legacy_outcome(evaluation)
        else:
            outcome = getattr(evaluation, "outcome", AssessmentEvaluationOutcome.INDETERMINATE)
        if outcome in {AssessmentEvaluationOutcome.INDETERMINATE, AssessmentEvaluationOutcome.NOT_EVALUABLE}:
            return ResolvedEvidencePolicy(
                policy_code=f"{purpose.upper()}_EVIDENCE_POLICY",
                policy_version=self.POLICY_VERSION,
                can_create_evidence=False,
                evidence_polarity="NONE",
                reason_code=f"EVALUATION_{outcome.upper()}",
            )
        polarity = "SUPPORTING" if outcome == AssessmentEvaluationOutcome.CORRECT else "CONTRADICTING"
        if purpose == AssessmentPurpose.CONCEPT_CHECK and outcome == AssessmentEvaluationOutcome.CORRECT:
            return ResolvedEvidencePolicy(
                policy_code=f"{purpose.upper()}_EVIDENCE_POLICY",
                policy_version=self.POLICY_VERSION,
                can_create_evidence=False,
                evidence_polarity="NONE",
                reason_code="PURPOSE_EXCLUDED",
            )
        return ResolvedEvidencePolicy(
            policy_code=f"{purpose.upper()}_EVIDENCE_POLICY",
            policy_version=self.POLICY_VERSION,
            can_create_evidence=True,
            evidence_polarity=polarity,
        )

    def _legacy_outcome(self, evaluation: AssessmentEvaluation) -> str:
        if getattr(evaluation, "is_correct", None) is True:
            return AssessmentEvaluationOutcome.CORRECT
        if getattr(evaluation, "is_correct", None) is False:
            return AssessmentEvaluationOutcome.INCORRECT
        score = getattr(evaluation, "score", None)
        max_score = getattr(evaluation, "max_score", None)
        if score is None or max_score in {None, 0}:
            return AssessmentEvaluationOutcome.PARTIALLY_CORRECT
        ratio = score / max_score
        if ratio >= 1.0:
            return AssessmentEvaluationOutcome.CORRECT
        if ratio > 0:
            return AssessmentEvaluationOutcome.PARTIALLY_CORRECT
        return AssessmentEvaluationOutcome.INCORRECT
