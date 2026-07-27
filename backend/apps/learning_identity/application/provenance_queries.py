from __future__ import annotations

from django.core.exceptions import PermissionDenied

from apps.users.domain.models import InstitutionMembership, InstitutionRole, User

from ..domain.enums import AttributeVisibility, EvidenceLinkStatus, EvidenceRelationship
from ..domain.models import LearnerLearningProfile, LearningIdentityAttribute, LearningIdentityEvidenceLink, LearningProfileVersion
from .provenance import evaluate_profile_version_provenance
from .provenance_dto import EvidenceLinkSummary


def _has_access(actor: User, profile: LearnerLearningProfile) -> bool:
    if actor.id == profile.learner_id:
        return True
    if actor.is_superuser:
        return True
    return InstitutionMembership.objects.filter(
        user=actor,
        institution_id=profile.tenant_id,
        is_active=True,
        role__in=[
            InstitutionRole.ADMINISTRATOR,
            InstitutionRole.INSTITUTION_OWNER,
            InstitutionRole.SYSTEM_ADMINISTRATOR,
            InstitutionRole.TEACHER,
            InstitutionRole.REVIEWER,
        ],
    ).exists()


def _summary(link: LearningIdentityEvidenceLink) -> EvidenceLinkSummary:
    return EvidenceLinkSummary(
        evidence_link_id=str(link.id),
        attribute_id=str(link.attribute_id),
        attribute_type=link.attribute.attribute_type,
        classification=link.attribute.classification,
        source_domain=link.source_domain,
        source_type=link.source_type,
        relationship=link.relationship,
        authority_class=link.authority_class,
        status=link.status,
        safe_summary=link.safe_summary,
        review_required=link.review_required,
        reason_codes=link.reason_codes or [],
    )


class GetAttributeProvenance:
    def execute(self, *, attribute_id, actor: User) -> list[EvidenceLinkSummary]:
        attribute = LearningIdentityAttribute.objects.select_related("profile_version__profile").get(id=attribute_id)
        if not _has_access(actor, attribute.profile_version.profile):
            raise PermissionDenied("LEARNING_IDENTITY_ACCESS_DENIED")
        return [
            _summary(link)
            for link in attribute.evidence_links.select_related("attribute").order_by("relationship", "source_domain", "source_type", "source_identifier", "source_revision")
        ]


class ListProfileVersionEvidence:
    def execute(self, *, profile_version_id, actor: User) -> list[EvidenceLinkSummary]:
        version = LearningProfileVersion.objects.select_related("profile").get(id=profile_version_id)
        if not _has_access(actor, version.profile):
            raise PermissionDenied("LEARNING_IDENTITY_ACCESS_DENIED")
        links = (
            LearningIdentityEvidenceLink.objects.select_related("attribute")
            .filter(attribute__profile_version=version)
            .order_by("attribute__attribute_type", "relationship", "source_domain", "source_type", "source_identifier", "source_revision")
        )
        return [_summary(link) for link in links]


class GetProfileVersionProvenanceReadiness:
    def execute(self, *, profile_version_id, actor: User):
        version = LearningProfileVersion.objects.select_related("profile").prefetch_related("attributes__evidence_links").get(id=profile_version_id)
        if not _has_access(actor, version.profile):
            raise PermissionDenied("LEARNING_IDENTITY_ACCESS_DENIED")
        return evaluate_profile_version_provenance(version)


class GetLearnerSafeProvenanceSummary:
    def execute(self, *, profile_version_id, actor: User) -> list[str]:
        version = LearningProfileVersion.objects.select_related("profile").get(id=profile_version_id)
        if not _has_access(actor, version.profile):
            raise PermissionDenied("LEARNING_IDENTITY_ACCESS_DENIED")
        safe: list[str] = []
        links = (
            LearningIdentityEvidenceLink.objects.select_related("attribute")
            .filter(attribute__profile_version=version)
            .exclude(summary_visibility__in=[AttributeVisibility.RESTRICTED, AttributeVisibility.SYSTEM_ONLY])
            .order_by("attribute__attribute_type", "relationship", "source_domain", "source_type", "created_at")
        )
        for link in links:
            if link.status == EvidenceLinkStatus.INVALIDATED:
                safe.append("A source for this information is no longer trusted.")
            elif link.status == EvidenceLinkStatus.WITHDRAWN:
                safe.append("A source for this information was withdrawn.")
            elif link.status == EvidenceLinkStatus.STALE:
                safe.append("This information may be out of date.")
            elif link.relationship == EvidenceRelationship.CONTRADICTS:
                safe.append("Conflicting information requires review.")
            elif link.safe_summary:
                safe.append(link.safe_summary)
        return safe
