from datetime import date

from apps.self_study.curriculum_models import CandidateEligibility, MatchClassification
from apps.self_study.domain.curriculum_resolution import (
    CandidateFacts,
    ResolutionInput,
    evaluate_candidate,
)


def request():
    return ResolutionInput(
        goal="advanced mathematics calculus",
        subject_area="mathematics",
        target_credential="",
        preferred_authority="",
        jurisdiction="LS",
        preferred_language="en",
        education_context="",
        permitted_sources=(
            "LEARNER_SUPPLIED_OFFICIAL",
            "INSTITUTION_OR_QUALIFICATION",
            "NATIONAL_OR_REGIONAL",
            "PROFESSIONAL_OR_ACCREDITATION",
            "APPROVED_CURATED_REFERENCE",
            "GOVERNED_COMPOSITE",
        ),
        permitted_licences=("CC-BY",),
        tenant_id="tenant-one",
        today=date(2026, 7, 20),
    )


def facts(**changes):
    values = {
        "source_classification": "NATIONAL_OR_REGIONAL",
        "subject_area": "mathematics",
        "title": "Advanced mathematics and calculus",
        "outcomes": "advanced mathematics calculus",
        "credential_identifier": "",
        "qualification_type": "",
        "jurisdiction": "LS",
        "education_stage": "",
        "language": "en",
        "official_translation_languages": (),
        "generated_translation_permitted": False,
        "authority_key": "national-body",
        "authority_verification": "VERIFIED",
        "authority_status": "ACTIVE",
        "reference_status": "ACTIVE",
        "reference_tenant_id": "",
        "version_status": "ACTIVE",
        "provenance_status": "COMPLETE",
        "licence_identifier": "CC-BY",
        "effective_from": date(2025, 1, 1),
        "effective_until": None,
    }
    values.update(changes)
    return CandidateFacts(**values)


def test_deterministic_candidate_evaluation_records_explicit_components():
    first = evaluate_candidate(request(), facts())
    second = evaluate_candidate(request(), facts())
    assert first == second
    assert first.eligibility == CandidateEligibility.ELIGIBLE
    assert first.match_classification in {MatchClassification.EXACT, MatchClassification.STRONG}
    assert set(first.score_components) >= {
        "subject_alignment",
        "goal_outcome_alignment",
        "authority_trust",
        "licence_compatibility",
    }


def test_hard_constraint_defeats_high_alignment_score():
    result = evaluate_candidate(
        request(),
        facts(authority_verification="UNVERIFIED"),
    )
    assert result.eligibility == CandidateEligibility.INELIGIBLE
    assert result.match_classification == MatchClassification.INCOMPATIBLE
    assert "AUTHORITY_NOT_VERIFIED" in result.rejection_reasons


def test_generated_translation_is_distinct_from_official_version():
    result = evaluate_candidate(
        request(),
        facts(language="fr", generated_translation_permitted=True),
    )
    assert result.eligibility == CandidateEligibility.ELIGIBLE
    assert result.language_disposition == "GENERATED_TRANSLATION_REQUIRED"


def test_suspended_version_and_unknown_licence_fail_closed():
    result = evaluate_candidate(
        request(),
        facts(version_status="SUSPENDED", licence_identifier="UNKNOWN"),
    )
    assert result.eligibility == CandidateEligibility.INELIGIBLE
    assert "CURRICULUM_SUSPENDED" in result.rejection_reasons
    assert "LICENCE_NOT_PERMITTED" in result.rejection_reasons
