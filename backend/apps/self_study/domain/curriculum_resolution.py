from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..curriculum_models import (
    CandidateEligibility,
    CurriculumVersionStatus,
    LanguageDisposition,
    MatchClassification,
    ProvenanceStatus,
    SourceClassification,
    VerificationStatus,
)

RESOLVER_ALGORITHM_VERSION = "pi-6f.2-rules-v1"
SOURCE_HIERARCHY = {
    SourceClassification.LEARNER_SUPPLIED_OFFICIAL: 1,
    SourceClassification.INSTITUTION_OR_QUALIFICATION: 2,
    SourceClassification.NATIONAL_OR_REGIONAL: 3,
    SourceClassification.PROFESSIONAL_OR_ACCREDITATION: 4,
    SourceClassification.CURATED_REFERENCE: 5,
    SourceClassification.COMPOSITE: 6,
}
POLICY_SOURCE_NAMES = {
    SourceClassification.LEARNER_SUPPLIED_OFFICIAL: "LEARNER_SUPPLIED_OFFICIAL",
    SourceClassification.INSTITUTION_OR_QUALIFICATION: "INSTITUTION_OR_QUALIFICATION",
    SourceClassification.NATIONAL_OR_REGIONAL: "NATIONAL_OR_REGIONAL",
    SourceClassification.PROFESSIONAL_OR_ACCREDITATION: "PROFESSIONAL_OR_ACCREDITATION",
    SourceClassification.CURATED_REFERENCE: "APPROVED_CURATED_REFERENCE",
    SourceClassification.COMPOSITE: "GOVERNED_COMPOSITE",
}


@dataclass(frozen=True)
class ResolutionInput:
    goal: str
    subject_area: str
    target_credential: str
    preferred_authority: str
    jurisdiction: str
    preferred_language: str
    education_context: str
    permitted_sources: tuple[str, ...]
    permitted_licences: tuple[str, ...]
    tenant_id: str
    today: date


@dataclass(frozen=True)
class CandidateFacts:
    source_classification: str
    subject_area: str
    title: str
    outcomes: str
    credential_identifier: str
    qualification_type: str
    jurisdiction: str
    education_stage: str
    language: str
    official_translation_languages: tuple[str, ...]
    generated_translation_permitted: bool
    authority_key: str
    authority_verification: str
    authority_status: str
    reference_status: str
    reference_tenant_id: str
    version_status: str
    provenance_status: str
    licence_identifier: str
    effective_from: date | None
    effective_until: date | None


@dataclass(frozen=True)
class CandidateEvaluation:
    hierarchy_rank: int
    eligibility: str
    match_classification: str
    language_disposition: str
    score_components: dict[str, int]
    total_score: Decimal
    confidence: Decimal
    requires_approval: bool
    rejection_reasons: tuple[str, ...]


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _alignment(left: str, right: str) -> int:
    lhs, rhs = _tokens(left), _tokens(right)
    if not lhs or not rhs:
        return 0
    return round(100 * len(lhs & rhs) / len(lhs))


def evaluate_candidate(request: ResolutionInput, facts: CandidateFacts) -> CandidateEvaluation:
    reasons: list[str] = []
    if facts.version_status == CurriculumVersionStatus.SUSPENDED:
        reasons.append("CURRICULUM_SUSPENDED")
    elif facts.version_status == CurriculumVersionStatus.WITHDRAWN:
        reasons.append("CURRICULUM_WITHDRAWN")
    elif facts.version_status != CurriculumVersionStatus.ACTIVE:
        reasons.append("CURRICULUM_NOT_ACTIVE")
    if facts.authority_verification != VerificationStatus.VERIFIED or facts.authority_status != "ACTIVE":
        reasons.append("AUTHORITY_NOT_VERIFIED")
    if facts.reference_status != "ACTIVE":
        reasons.append("CURRICULUM_SUSPENDED")
    if facts.provenance_status != ProvenanceStatus.COMPLETE:
        reasons.append("PROVENANCE_INCOMPLETE")
    if POLICY_SOURCE_NAMES[facts.source_classification] not in request.permitted_sources:
        reasons.append("SOURCE_CLASS_NOT_PERMITTED")
    if facts.licence_identifier not in request.permitted_licences:
        reasons.append("LICENCE_NOT_PERMITTED")
    if facts.reference_tenant_id and facts.reference_tenant_id != request.tenant_id:
        reasons.append("INSTITUTIONAL_SCOPE_MISMATCH")
    if facts.effective_from and request.today < facts.effective_from:
        reasons.append("VERSION_OUTSIDE_EFFECTIVE_PERIOD")
    if facts.effective_until and request.today > facts.effective_until:
        reasons.append("VERSION_OUTSIDE_EFFECTIVE_PERIOD")
    if request.jurisdiction and facts.jurisdiction and request.jurisdiction.casefold() != facts.jurisdiction.casefold():
        reasons.append("JURISDICTION_MISMATCH")

    subject_score = max(
        _alignment(request.subject_area, facts.subject_area),
        _alignment(request.goal, facts.subject_area),
    )
    outcome_score = _alignment(request.goal, f"{facts.title} {facts.outcomes}")
    credential_score = (
        100
        if request.target_credential
        and request.target_credential.casefold() in {
            facts.credential_identifier.casefold(),
            facts.qualification_type.casefold(),
        }
        else 0
    )
    if subject_score == 0:
        reasons.append("SUBJECT_MISMATCH")

    if facts.language == request.preferred_language:
        language_disposition = LanguageDisposition.NATIVE_LANGUAGE
        language_score = 100
    elif request.preferred_language in facts.official_translation_languages:
        language_disposition = LanguageDisposition.OFFICIAL_TRANSLATION
        language_score = 90
    elif facts.generated_translation_permitted:
        language_disposition = LanguageDisposition.GENERATED_TRANSLATION_REQUIRED
        language_score = 65
    else:
        language_disposition = LanguageDisposition.NATIVE_LANGUAGE
        language_score = 0
        reasons.append("LANGUAGE_NOT_SUPPORTED")

    components = {
        "subject_alignment": subject_score,
        "goal_outcome_alignment": outcome_score,
        "credential_alignment": credential_score,
        "jurisdiction_alignment": 100 if not request.jurisdiction or request.jurisdiction.casefold() == facts.jurisdiction.casefold() else 0,
        "language_compatibility": language_score,
        "education_stage_compatibility": 100 if not request.education_context or request.education_context.casefold() == facts.education_stage.casefold() else 50,
        "preferred_authority_match": 100 if request.preferred_authority and request.preferred_authority.casefold() == facts.authority_key.casefold() else 0,
        "effective_date_validity": 0 if "VERSION_OUTSIDE_EFFECTIVE_PERIOD" in reasons else 100,
        "provenance_quality": 100 if facts.provenance_status == ProvenanceStatus.COMPLETE else 0,
        "authority_trust": 100 if facts.authority_verification == VerificationStatus.VERIFIED else 0,
        "licence_compatibility": 100 if facts.licence_identifier in request.permitted_licences else 0,
    }
    total = Decimal(
        str(
            round(
                components["subject_alignment"] * 0.25
                + components["goal_outcome_alignment"] * 0.25
                + components["credential_alignment"] * 0.10
                + components["jurisdiction_alignment"] * 0.05
                + components["language_compatibility"] * 0.10
                + components["education_stage_compatibility"] * 0.05
                + components["preferred_authority_match"] * 0.05
                + components["effective_date_validity"] * 0.05
                + components["provenance_quality"] * 0.04
                + components["authority_trust"] * 0.04
                + components["licence_compatibility"] * 0.02,
                2,
            )
        )
    )
    hard_reasons = tuple(dict.fromkeys(reasons))
    eligibility = CandidateEligibility.INELIGIBLE if hard_reasons else CandidateEligibility.ELIGIBLE
    if eligibility == CandidateEligibility.INELIGIBLE:
        classification = MatchClassification.INCOMPATIBLE
    elif total >= 85:
        classification = MatchClassification.EXACT
    elif total >= 70:
        classification = MatchClassification.STRONG
    elif total >= 50:
        classification = MatchClassification.PARTIAL
    else:
        classification = MatchClassification.WEAK
    return CandidateEvaluation(
        hierarchy_rank=SOURCE_HIERARCHY[facts.source_classification],
        eligibility=eligibility,
        match_classification=classification,
        language_disposition=language_disposition,
        score_components=components,
        total_score=total,
        confidence=(total / Decimal("100")).quantize(Decimal("0.0001")),
        requires_approval=classification == MatchClassification.PARTIAL,
        rejection_reasons=hard_reasons,
    )
