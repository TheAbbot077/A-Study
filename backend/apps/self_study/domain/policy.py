from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class AcquisitionDecision(StrEnum):
    AUTO_APPROVED = "AUTO_APPROVED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    LINK_ONLY = "LINK_ONLY"
    REJECTED = "REJECTED"


class AcquisitionReason(StrEnum):
    PROVIDER_NOT_ALLOWED = "PROVIDER_NOT_ALLOWED"
    SOURCE_CATEGORY_NOT_ALLOWED = "SOURCE_CATEGORY_NOT_ALLOWED"
    UNKNOWN_LICENCE = "UNKNOWN_LICENCE"
    LICENCE_NOT_ALLOWED = "LICENCE_NOT_ALLOWED"
    PAID_RESOURCE_REQUIRES_APPROVAL = "PAID_RESOURCE_REQUIRES_APPROVAL"
    PAID_RESOURCE_NOT_ALLOWED = "PAID_RESOURCE_NOT_ALLOWED"
    SIZE_LIMIT_EXCEEDED = "SIZE_LIMIT_EXCEEDED"
    TOTAL_SIZE_LIMIT_EXCEEDED = "TOTAL_SIZE_LIMIT_EXCEEDED"
    LANGUAGE_NOT_ALLOWED = "LANGUAGE_NOT_ALLOWED"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    COST_LIMIT_EXCEEDED = "COST_LIMIT_EXCEEDED"
    TRUST_REQUIREMENT_NOT_MET = "TRUST_REQUIREMENT_NOT_MET"
    AUTOMATIC_ACQUISITION_DISABLED = "AUTOMATIC_ACQUISITION_DISABLED"
    EXTERNAL_NETWORK_ACCESS_DISABLED = "EXTERNAL_NETWORK_ACCESS_DISABLED"
    POLICY_ALLOWS_AUTOMATIC_ACQUISITION = "POLICY_ALLOWS_AUTOMATIC_ACQUISITION"
    RESTRICTED_RESOURCE_IS_LINK_ONLY = "RESTRICTED_RESOURCE_IS_LINK_ONLY"
    RESOURCE_METADATA_INCOMPLETE = "RESOURCE_METADATA_INCOMPLETE"


def _intersection(higher: frozenset[str], lower: frozenset[str]) -> frozenset[str]:
    if not lower:
        return higher
    return higher.intersection(lower)


def _minimum(higher: int | Decimal | None, lower: int | Decimal | None):
    if higher is None:
        return lower
    if lower is None:
        return higher
    return min(higher, lower)


@dataclass(frozen=True)
class PolicyLayer:
    automatic_acquisition_enabled: bool = True
    allowed_provider_ids: frozenset[str] = frozenset()
    allowed_source_categories: frozenset[str] = frozenset()
    allowed_licence_categories: frozenset[str] = frozenset()
    allowed_mime_types: frozenset[str] = frozenset()
    allowed_languages: frozenset[str] = frozenset()
    maximum_resource_count: int | None = None
    maximum_single_file_bytes: int | None = None
    maximum_total_bytes: int | None = None
    maximum_cost: Decimal | None = None
    cost_currency: str = "USD"
    paid_content_allowed: bool = False
    unknown_licence_allowed: bool = False
    link_only_when_restricted: bool = True
    user_approval_threshold: Decimal | None = None
    retention_policy: str = "RETAIN_WITH_JOURNEY"
    external_network_access_enabled: bool = False
    autonomous_curriculum_fallback_allowed: bool = False


@dataclass(frozen=True)
class EffectivePolicy(PolicyLayer):
    purpose_disclosure_required: bool = True
    raw_scores_visible: bool = False
    comparative_ranking_allowed: bool = False
    learner_can_retake: bool = True
    learner_can_challenge: bool = True
    learner_can_attempt_checkpoint: bool = True
    formal_grade_effect: bool = False
    transcript_effect: bool = False


def resolve_effective_policy(*layers: PolicyLayer) -> EffectivePolicy:
    if not layers:
        raise ValueError("At least one policy layer is required.")
    result = layers[0]
    retention_rank = {
        "DO_NOT_RETAIN": 0,
        "RETAIN_UNTIL_JOURNEY_END": 1,
        "RETAIN_WITH_JOURNEY": 2,
    }
    if any(layer.retention_policy not in retention_rank for layer in layers):
        raise ValueError("Retention policy is invalid.")
    for lower in layers[1:]:
        if lower.cost_currency != result.cost_currency and lower.maximum_cost is not None:
            raise ValueError("Cost limits must use the higher authority currency.")
        result = PolicyLayer(
            automatic_acquisition_enabled=result.automatic_acquisition_enabled and lower.automatic_acquisition_enabled,
            allowed_provider_ids=_intersection(result.allowed_provider_ids, lower.allowed_provider_ids),
            allowed_source_categories=_intersection(result.allowed_source_categories, lower.allowed_source_categories),
            allowed_licence_categories=_intersection(result.allowed_licence_categories, lower.allowed_licence_categories),
            allowed_mime_types=_intersection(result.allowed_mime_types, lower.allowed_mime_types),
            allowed_languages=_intersection(result.allowed_languages, lower.allowed_languages),
            maximum_resource_count=_minimum(result.maximum_resource_count, lower.maximum_resource_count),
            maximum_single_file_bytes=_minimum(result.maximum_single_file_bytes, lower.maximum_single_file_bytes),
            maximum_total_bytes=_minimum(result.maximum_total_bytes, lower.maximum_total_bytes),
            maximum_cost=_minimum(result.maximum_cost, lower.maximum_cost),
            cost_currency=result.cost_currency,
            paid_content_allowed=result.paid_content_allowed and lower.paid_content_allowed,
            unknown_licence_allowed=result.unknown_licence_allowed and lower.unknown_licence_allowed,
            link_only_when_restricted=result.link_only_when_restricted or lower.link_only_when_restricted,
            user_approval_threshold=_minimum(result.user_approval_threshold, lower.user_approval_threshold),
            retention_policy=min(
                (result.retention_policy, lower.retention_policy),
                key=lambda value: retention_rank[value],
            ),
            external_network_access_enabled=result.external_network_access_enabled and lower.external_network_access_enabled,
            autonomous_curriculum_fallback_allowed=(
                result.autonomous_curriculum_fallback_allowed and lower.autonomous_curriculum_fallback_allowed
            ),
        )
    return EffectivePolicy(**result.__dict__)


@dataclass(frozen=True)
class AcquisitionCandidate:
    provider_id: str
    source_category: str
    licence_category: str
    mime_type: str
    language: str
    file_size: int
    projected_total_size: int
    projected_resource_count: int
    price: Decimal
    currency: str
    trust_classification: str
    network_acquisition_required: bool
    restricted: bool = False


def authorize_candidate(policy: EffectivePolicy, candidate: AcquisitionCandidate) -> tuple[AcquisitionDecision, tuple[str, ...]]:
    required = (
        candidate.provider_id,
        candidate.source_category,
        candidate.licence_category,
        candidate.mime_type,
        candidate.language,
        candidate.currency,
        candidate.trust_classification,
    )
    if not all(value.strip() for value in required):
        return AcquisitionDecision.REJECTED, (AcquisitionReason.RESOURCE_METADATA_INCOMPLETE,)
    checks: list[AcquisitionReason] = []
    if candidate.provider_id not in policy.allowed_provider_ids:
        checks.append(AcquisitionReason.PROVIDER_NOT_ALLOWED)
    if candidate.source_category not in policy.allowed_source_categories:
        checks.append(AcquisitionReason.SOURCE_CATEGORY_NOT_ALLOWED)
    if candidate.licence_category == "UNKNOWN" and not policy.unknown_licence_allowed:
        checks.append(AcquisitionReason.UNKNOWN_LICENCE)
    elif candidate.licence_category not in policy.allowed_licence_categories:
        checks.append(AcquisitionReason.LICENCE_NOT_ALLOWED)
    if candidate.mime_type not in policy.allowed_mime_types:
        checks.append(AcquisitionReason.UNSUPPORTED_FILE_TYPE)
    if candidate.language not in policy.allowed_languages:
        checks.append(AcquisitionReason.LANGUAGE_NOT_ALLOWED)
    if policy.maximum_single_file_bytes is not None and candidate.file_size > policy.maximum_single_file_bytes:
        checks.append(AcquisitionReason.SIZE_LIMIT_EXCEEDED)
    if policy.maximum_total_bytes is not None and candidate.projected_total_size > policy.maximum_total_bytes:
        checks.append(AcquisitionReason.TOTAL_SIZE_LIMIT_EXCEEDED)
    if policy.maximum_resource_count is not None and candidate.projected_resource_count > policy.maximum_resource_count:
        checks.append(AcquisitionReason.RESOURCE_LIMIT_EXCEEDED)
    if candidate.currency != policy.cost_currency:
        checks.append(AcquisitionReason.COST_LIMIT_EXCEEDED)
    elif policy.maximum_cost is not None and candidate.price > policy.maximum_cost:
        checks.append(AcquisitionReason.COST_LIMIT_EXCEEDED)
    if candidate.price > 0 and not policy.paid_content_allowed:
        checks.append(AcquisitionReason.PAID_RESOURCE_NOT_ALLOWED)
    if candidate.trust_classification not in {"PLATFORM_VERIFIED", "INSTITUTION_VERIFIED", "PROVIDER_VERIFIED"}:
        checks.append(AcquisitionReason.TRUST_REQUIREMENT_NOT_MET)
    if candidate.network_acquisition_required and not policy.external_network_access_enabled:
        checks.append(AcquisitionReason.EXTERNAL_NETWORK_ACCESS_DISABLED)
    if checks:
        if candidate.restricted and policy.link_only_when_restricted and set(checks).issubset(
            {AcquisitionReason.LICENCE_NOT_ALLOWED, AcquisitionReason.UNKNOWN_LICENCE}
        ):
            return AcquisitionDecision.LINK_ONLY, (AcquisitionReason.RESTRICTED_RESOURCE_IS_LINK_ONLY,)
        return AcquisitionDecision.REJECTED, tuple(dict.fromkeys(checks))
    if candidate.price > 0 and policy.user_approval_threshold is not None and candidate.price >= policy.user_approval_threshold:
        return AcquisitionDecision.APPROVAL_REQUIRED, (AcquisitionReason.PAID_RESOURCE_REQUIRES_APPROVAL,)
    if not policy.automatic_acquisition_enabled:
        return AcquisitionDecision.APPROVAL_REQUIRED, (AcquisitionReason.AUTOMATIC_ACQUISITION_DISABLED,)
    return AcquisitionDecision.AUTO_APPROVED, (AcquisitionReason.POLICY_ALLOWS_AUTOMATIC_ACQUISITION,)
