from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from apps.assessments.domain.models import AssessmentExperience, AssessmentPurpose
from apps.study_lab.domain.capabilities import StudyLabCapability


@dataclass(frozen=True)
class AssessmentCapabilityEntry:
    code: str
    disposition: str
    availability: str
    usable: bool
    reason_code: str | None = None
    restriction: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["reason_code"] is None:
            data.pop("reason_code")
        if data["restriction"] is None:
            data.pop("restriction")
        return data


class AssessmentEnvironmentService:
    POLICY_VERSION = "1"

    PURPOSE_POLICIES: dict[str, dict[str, dict[str, Any]]] = {
        AssessmentPurpose.CONCEPT_CHECK: {
            StudyLabCapability.STUDY_LAB_USE: {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "SCRATCHPAD": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "SCIENTIFIC_CALCULATOR": {"disposition": "RESTRICTED", "availability": "AVAILABLE", "restriction": {"restricted_operation_set": ["basic_arithmetic", "numeric_entry"]}},
            "GRAPHING_CALCULATOR": {"disposition": "PROHIBITED", "availability": "AVAILABLE", "reason_code": "GRAPHING_CALCULATOR_NOT_PERMITTED"},
            "CODE_EDITOR": {"disposition": "PROHIBITED", "availability": "AVAILABLE", "reason_code": "CODE_EDITOR_NOT_PERMITTED"},
            "CODE_EXECUTION": {"disposition": "PROHIBITED", "availability": "AVAILABLE", "reason_code": "CODE_EXECUTION_NOT_PERMITTED"},
            "ABBOT": {"disposition": "PROHIBITED", "availability": "AVAILABLE", "reason_code": "TUTOR_ASSISTANCE_NOT_PERMITTED"},
            "ARIEL": {"disposition": "PROHIBITED", "availability": "AVAILABLE", "reason_code": "COMPANION_ASSISTANCE_NOT_PERMITTED"},
            "AI_SCAFFOLD_GENERATION": {"disposition": "PROHIBITED", "availability": "AVAILABLE", "reason_code": "GENERATIVE_ASSISTANCE_NOT_PERMITTED"},
            "EXTERNAL_RESOURCES": {"disposition": "PROHIBITED", "availability": "AVAILABLE", "reason_code": "EXTERNAL_RESOURCES_NOT_PERMITTED"},
            "PRIVATE_NOTES": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "ASSESSMENT_PROVIDED_REFERENCE": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
        },
        AssessmentPurpose.PRACTICE: {
            StudyLabCapability.STUDY_LAB_USE: {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "SCRATCHPAD": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "SCIENTIFIC_CALCULATOR": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "GRAPHING_CALCULATOR": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "CODE_EDITOR": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "CODE_EXECUTION": {"disposition": "RESTRICTED", "availability": "AVAILABLE", "restriction": {"restricted_operation_set": ["single_run"]}},
            "ABBOT": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "ARIEL": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "AI_SCAFFOLD_GENERATION": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "EXTERNAL_RESOURCES": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "PRIVATE_NOTES": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
            "ASSESSMENT_PROVIDED_REFERENCE": {"disposition": "ALLOWED", "availability": "AVAILABLE"},
        },
    }

    DEFAULT_CAPABILITIES = {
        StudyLabCapability.STUDY_LAB_USE,
        "SCRATCHPAD",
        "SCIENTIFIC_CALCULATOR",
        "GRAPHING_CALCULATOR",
        "CODE_EDITOR",
        "CODE_EXECUTION",
        "ABBOT",
        "ARIEL",
        "AI_SCAFFOLD_GENERATION",
        "EXTERNAL_RESOURCES",
        "PRIVATE_NOTES",
        "ASSESSMENT_PROVIDED_REFERENCE",
    }

    def resolve_policy(self, experience: AssessmentExperience) -> dict[str, Any]:
        policy_rules = self.PURPOSE_POLICIES.get(experience.purpose, self.PURPOSE_POLICIES[AssessmentPurpose.PRACTICE])
        capabilities = []
        blockers: list[dict[str, Any]] = []
        for capability_code in sorted(self.DEFAULT_CAPABILITIES):
            rule = policy_rules.get(capability_code, {"disposition": "ALLOWED", "availability": "AVAILABLE"})
            entry = AssessmentCapabilityEntry(
                code=capability_code,
                disposition=rule["disposition"],
                availability=rule["availability"],
                usable=rule["disposition"] in {"ALLOWED", "RESTRICTED"} and rule["availability"] == "AVAILABLE",
                reason_code=rule.get("reason_code"),
                restriction=rule.get("restriction"),
            )
            capabilities.append(entry.to_dict())
            if not entry.usable and entry.disposition in {"PROHIBITED", "RESTRICTED"} and entry.reason_code:
                blockers.append({"capability_code": capability_code, "reason_code": entry.reason_code})

        state = "READY"
        if experience.purpose == AssessmentPurpose.CONCEPT_CHECK:
            state = "READY"
        if any(item["disposition"] == "RESTRICTED" and item["availability"] != "AVAILABLE" for item in capabilities):
            state = "DEGRADED"

        return {
            "policy": {
                "code": f"{experience.purpose.upper()}_STANDARD",
                "version": self.POLICY_VERSION,
            },
            "state": state,
            "capabilities": capabilities,
            "blockers": blockers,
            "resolved_at": None,
            "source_checksum": f"{experience.purpose}:{self.POLICY_VERSION}",
        }

