from __future__ import annotations

from django.utils import timezone

from ..domain.enums import (
    AttributeClassification,
    EvidenceAuthorityClass,
    EvidenceLinkStatus,
    EvidenceRelationship,
    LearningProfileStatus,
    ProvenanceReadinessStatus,
    ProvenanceReasonCode,
)
from ..domain.models import LearnerLearningProfile, LearningIdentityAttribute, LearningIdentityEvidenceLink, LearningProfileVersion
from .provenance_dto import AttributeProvenanceResult, ProfileVersionProvenanceReadiness


AUTHORITATIVE_CLASSES = {EvidenceAuthorityClass.INSTITUTIONAL, EvidenceAuthorityClass.ASSESSMENT, EvidenceAuthorityClass.DIAGNOSTIC, EvidenceAuthorityClass.SYSTEM}
GOVERNED_EVIDENCE_CLASSES = {
    EvidenceAuthorityClass.ASSESSMENT,
    EvidenceAuthorityClass.DIAGNOSTIC,
    EvidenceAuthorityClass.OBSERVATIONAL,
    EvidenceAuthorityClass.SYSTEM,
}


def relationship_allowed(*, relationship: str, authority_class: str, classification: str) -> bool:
    if relationship == EvidenceRelationship.CONFIRMS:
        return authority_class in AUTHORITATIVE_CLASSES
    if relationship == EvidenceRelationship.CONTRADICTS:
        return authority_class in EvidenceAuthorityClass.values
    if relationship == EvidenceRelationship.SUPPORTS:
        return authority_class in EvidenceAuthorityClass.values
    if relationship == EvidenceRelationship.CONTEXTUALIZES:
        return True
    if relationship == EvidenceRelationship.SUPERSEDES:
        return True
    return False


def evaluate_attribute_provenance(attribute: LearningIdentityAttribute) -> AttributeProvenanceResult:
    links = list(attribute.evidence_links.all())
    active_links = [link for link in links if link.status == EvidenceLinkStatus.ACTIVE]
    authoritative_links = [
        link for link in active_links
        if link.relationship == EvidenceRelationship.CONFIRMS and link.authority_class in AUTHORITATIVE_CLASSES
    ]
    contradictions = [link for link in active_links if link.relationship == EvidenceRelationship.CONTRADICTS]
    stale_links = [link for link in links if link.status == EvidenceLinkStatus.STALE]
    blocking: list[str] = []
    review: list[str] = []

    if attribute.classification == AttributeClassification.DECLARED:
        if not attribute.source_type or not attribute.declared_at:
            blocking.append(ProvenanceReasonCode.DECLARATION_SOURCE_REQUIRED)
    elif attribute.classification == AttributeClassification.VERIFIED:
        if not authoritative_links:
            blocking.append(ProvenanceReasonCode.AUTHORITATIVE_EVIDENCE_REQUIRED)
    elif attribute.classification == AttributeClassification.OBSERVED:
        if attribute.confidence is None:
            blocking.append(ProvenanceReasonCode.CONFIDENCE_REQUIRED)
        if not any(link.authority_class in GOVERNED_EVIDENCE_CLASSES for link in active_links):
            blocking.append(ProvenanceReasonCode.GOVERNED_EVIDENCE_REQUIRED)
    elif attribute.classification == AttributeClassification.DERIVED:
        if not attribute.source_reference.get("derivation_policy_id"):
            blocking.append(ProvenanceReasonCode.DERIVATION_POLICY_REQUIRED)
        if attribute.confidence is None:
            blocking.append(ProvenanceReasonCode.CONFIDENCE_REQUIRED)

    if contradictions:
        review.append(ProvenanceReasonCode.CONTRADICTORY_EVIDENCE)
    if any(link.status in {EvidenceLinkStatus.WITHDRAWN, EvidenceLinkStatus.INVALIDATED} for link in links):
        review.append(ProvenanceReasonCode.SOURCE_INVALIDATED)
    if stale_links:
        review.append(ProvenanceReasonCode.SOURCE_STALE)

    status = ProvenanceReadinessStatus.READY
    if blocking:
        status = ProvenanceReadinessStatus.BLOCKED
    elif review or attribute.review_required:
        status = ProvenanceReadinessStatus.NEEDS_REVIEW

    return AttributeProvenanceResult(
        attribute_id=str(attribute.id),
        classification=attribute.classification,
        status=status,
        reason_codes=sorted(set([*blocking, *review])),
        active_evidence_count=len(active_links),
        authoritative_evidence_count=len(authoritative_links),
        contradiction_count=len(contradictions),
        stale_evidence_count=len(stale_links),
    )


def evaluate_profile_version_provenance(profile_version: LearningProfileVersion) -> ProfileVersionProvenanceReadiness:
    attributes = profile_version.attributes.prefetch_related("evidence_links").order_by("attribute_type", "created_at")
    results = [evaluate_attribute_provenance(attribute) for attribute in attributes]
    blocking = sorted({code for result in results if result.status == ProvenanceReadinessStatus.BLOCKED for code in result.reason_codes})
    review = sorted({code for result in results if result.status == ProvenanceReadinessStatus.NEEDS_REVIEW for code in result.reason_codes})
    status = ProvenanceReadinessStatus.READY
    if blocking:
        status = ProvenanceReadinessStatus.BLOCKED
    elif review:
        status = ProvenanceReadinessStatus.NEEDS_REVIEW
    return ProfileVersionProvenanceReadiness(
        profile_version_id=str(profile_version.id),
        status=status,
        attribute_results=results,
        blocking_codes=blocking,
        review_codes=review,
        evaluated_at=timezone.now(),
    )


def apply_provenance_impact(profile: LearnerLearningProfile, attribute: LearningIdentityAttribute, link: LearningIdentityEvidenceLink) -> list[str]:
    reason_codes: list[str] = []
    if link.relationship == EvidenceRelationship.CONTRADICTS:
        attribute.review_required = True
        reason_codes.append(ProvenanceReasonCode.CONTRADICTORY_EVIDENCE)
        if profile.status == LearningProfileStatus.ACTIVE:
            profile.status = LearningProfileStatus.NEEDS_REVIEW
            profile.version += 1
    elif link.status in {EvidenceLinkStatus.INVALIDATED, EvidenceLinkStatus.WITHDRAWN}:
        result = evaluate_attribute_provenance(attribute)
        if result.status != ProvenanceReadinessStatus.READY:
            attribute.review_required = True
            reason_codes.extend(result.reason_codes)
            if profile.status == LearningProfileStatus.ACTIVE:
                profile.status = LearningProfileStatus.NEEDS_REVIEW
                profile.version += 1
    elif link.status == EvidenceLinkStatus.STALE:
        attribute.review_required = True
        reason_codes.append(ProvenanceReasonCode.SOURCE_STALE)
    return sorted(set(reason_codes))
