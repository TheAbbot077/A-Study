from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.assessments.domain.models import AssessmentEnvironmentPolicy, AssessmentItem


@dataclass(frozen=True)
class EvaluationPolicyValidationResult:
    valid: bool
    reason_code: str | None = None
    blockers: list[dict[str, Any]] = None


class ValidateEvaluationPolicyService:
    def validate(self, *, policy: AssessmentEnvironmentPolicy | None, item: AssessmentItem) -> EvaluationPolicyValidationResult:
        if policy is None or not isinstance(policy, AssessmentEnvironmentPolicy):
            return EvaluationPolicyValidationResult(valid=True, blockers=[])

        required_capabilities = set((item.metadata or {}).get("required_capabilities", []))
        policy_rules = {rule.capability_code: rule for rule in policy.rules.all()}
        blockers: list[dict[str, Any]] = []
        for capability_code in required_capabilities:
            rule = policy_rules.get(capability_code)
            if rule is None:
                return EvaluationPolicyValidationResult(
                    valid=False,
                    reason_code="ASSESSMENT_ENVIRONMENT_POLICY_CONFLICT",
                    blockers=[{"capability_code": capability_code, "reason_code": "REQUIRED_CAPABILITY_UNRESOLVED"}],
                )
            if rule.disposition == "PROHIBITED":
                blockers.append({"capability_code": capability_code, "reason_code": "ASSESSMENT_ENVIRONMENT_POLICY_CONFLICT"})
                return EvaluationPolicyValidationResult(
                    valid=False,
                    reason_code="ASSESSMENT_ENVIRONMENT_POLICY_CONFLICT",
                    blockers=blockers,
                )

        return EvaluationPolicyValidationResult(valid=True, blockers=blockers)
