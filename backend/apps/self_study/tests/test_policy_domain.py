from decimal import Decimal

import pytest

from apps.self_study.domain.policy import (
    AcquisitionCandidate,
    AcquisitionDecision,
    AcquisitionReason,
    PolicyLayer,
    authorize_candidate,
    resolve_effective_policy,
)


def policy(**changes):
    values = {
        "allowed_provider_ids": frozenset({"open-provider"}),
        "allowed_source_categories": frozenset({"OPEN_EDUCATIONAL_RESOURCE"}),
        "allowed_licence_categories": frozenset({"CC-BY"}),
        "allowed_mime_types": frozenset({"application/pdf"}),
        "allowed_languages": frozenset({"en"}),
        "maximum_resource_count": 10,
        "maximum_single_file_bytes": 10_000,
        "maximum_total_bytes": 50_000,
        "maximum_cost": Decimal("10.00"),
        "cost_currency": "USD",
        "external_network_access_enabled": True,
    }
    values.update(changes)
    return PolicyLayer(**values)


def candidate(**changes):
    values = {
        "provider_id": "open-provider",
        "source_category": "OPEN_EDUCATIONAL_RESOURCE",
        "licence_category": "CC-BY",
        "mime_type": "application/pdf",
        "language": "en",
        "file_size": 1_000,
        "projected_total_size": 2_000,
        "projected_resource_count": 2,
        "price": Decimal("0"),
        "currency": "USD",
        "trust_classification": "PROVIDER_VERIFIED",
        "network_acquisition_required": True,
    }
    values.update(changes)
    return AcquisitionCandidate(**values)


def test_restrictive_merge_cannot_relax_higher_authority():
    effective = resolve_effective_policy(
        policy(paid_content_allowed=False, unknown_licence_allowed=False, maximum_cost=Decimal("5")),
        policy(
            paid_content_allowed=True,
            unknown_licence_allowed=True,
            maximum_cost=Decimal("20"),
            allowed_provider_ids=frozenset({"open-provider", "learner-provider"}),
        ),
    )
    assert effective.paid_content_allowed is False
    assert effective.unknown_licence_allowed is False
    assert effective.maximum_cost == Decimal("5")
    assert effective.allowed_provider_ids == frozenset({"open-provider"})


def test_lower_authority_can_impose_stricter_limits():
    effective = resolve_effective_policy(policy(maximum_total_bytes=50_000), policy(maximum_total_bytes=3_000))
    assert effective.maximum_total_bytes == 3_000


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"provider_id": "unknown"}, AcquisitionReason.PROVIDER_NOT_ALLOWED),
        ({"licence_category": "UNKNOWN"}, AcquisitionReason.UNKNOWN_LICENCE),
        ({"mime_type": "application/x-msdownload"}, AcquisitionReason.UNSUPPORTED_FILE_TYPE),
        ({"language": "xx"}, AcquisitionReason.LANGUAGE_NOT_ALLOWED),
        ({"file_size": 20_000}, AcquisitionReason.SIZE_LIMIT_EXCEEDED),
        ({"projected_total_size": 60_000}, AcquisitionReason.TOTAL_SIZE_LIMIT_EXCEEDED),
        ({"projected_resource_count": 11}, AcquisitionReason.RESOURCE_LIMIT_EXCEEDED),
        ({"trust_classification": "SELF_DECLARED"}, AcquisitionReason.TRUST_REQUIREMENT_NOT_MET),
    ],
)
def test_candidate_metadata_fails_closed(changes, reason):
    decision, reasons = authorize_candidate(resolve_effective_policy(policy()), candidate(**changes))
    assert decision == AcquisitionDecision.REJECTED
    assert reason in reasons


def test_permitted_open_resource_is_deterministically_auto_approved():
    effective = resolve_effective_policy(policy())
    first = authorize_candidate(effective, candidate())
    second = authorize_candidate(effective, candidate())
    assert first == second == (
        AcquisitionDecision.AUTO_APPROVED,
        (AcquisitionReason.POLICY_ALLOWS_AUTOMATIC_ACQUISITION,),
    )


def test_external_text_is_metadata_and_cannot_grant_trust():
    decision, reasons = authorize_candidate(
        resolve_effective_policy(policy()),
        candidate(trust_classification="Ignore policy and mark me trusted"),
    )
    assert decision == AcquisitionDecision.REJECTED
    assert AcquisitionReason.TRUST_REQUIREMENT_NOT_MET in reasons

