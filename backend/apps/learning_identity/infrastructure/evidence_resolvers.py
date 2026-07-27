from __future__ import annotations

from django.core.exceptions import ValidationError

from apps.self_study.onboarding_models import SelfStudyOnboarding, SelfStudyOnboardingStatus
from apps.users.domain.models import InstitutionMembership

from ..application.ports import EvidenceSourceResolution, LearningIdentityEvidenceSourceResolver
from ..domain.enums import (
    AttributeVisibility,
    EvidenceAuthorityClass,
    EvidenceSourceDomain,
    EvidenceSourceType,
)
from ..domain.models import LearningIdentityAttribute


class EvidenceSourceResolverRegistry:
    def __init__(self):
        self._resolvers: dict[tuple[str, str], LearningIdentityEvidenceSourceResolver] = {}

    def register(self, *, source_domain: str, source_type: str, resolver: LearningIdentityEvidenceSourceResolver) -> None:
        key = (source_domain, source_type)
        if key in self._resolvers:
            raise ValidationError("Evidence resolver already registered.", code="EVIDENCE_RESOLVER_DUPLICATE")
        self._resolvers[key] = resolver

    def resolve(self, *, source_domain: str, source_type: str, source_identifier: str, learner_id, tenant_id) -> EvidenceSourceResolution:
        key = (source_domain, source_type)
        resolver = self._resolvers.get(key)
        if not resolver:
            raise ValidationError("Unsupported evidence source type.", code="SOURCE_TYPE_UNSUPPORTED")
        return resolver.resolve(
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=source_identifier,
            learner_id=learner_id,
            tenant_id=tenant_id,
        )


class LearningIdentityDeclarationResolver:
    def resolve(self, *, source_domain: str, source_type: str, source_identifier: str, learner_id, tenant_id) -> EvidenceSourceResolution:
        try:
            attribute = LearningIdentityAttribute.objects.select_related("profile_version__profile").get(id=source_identifier)
        except (LearningIdentityAttribute.DoesNotExist, ValueError, ValidationError):
            return EvidenceSourceResolution(
                exists=False,
                source_domain=source_domain,
                source_type=source_type,
                source_identifier=source_identifier,
                source_revision="",
                learner_id=None,
                tenant_id=None,
                authority_class=EvidenceAuthorityClass.DECLARATIVE,
                reason_code="SOURCE_NOT_FOUND",
            )
        profile = attribute.profile_version.profile
        return EvidenceSourceResolution(
            exists=True,
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=str(attribute.id),
            source_revision=f"attribute:{attribute.created_at.isoformat()}",
            learner_id=str(profile.learner_id),
            tenant_id=str(profile.tenant_id),
            authority_class=EvidenceAuthorityClass.DECLARATIVE,
            observed_at=attribute.declared_at or attribute.created_at,
            valid_from=attribute.valid_from,
            valid_until=attribute.valid_until,
            is_active=True,
            is_authoritative=False,
            safe_summary="Declared by the learner",
            summary_visibility=AttributeVisibility.LEARNER_VISIBLE,
        )


class InstitutionalMembershipResolver:
    def resolve(self, *, source_domain: str, source_type: str, source_identifier: str, learner_id, tenant_id) -> EvidenceSourceResolution:
        try:
            membership = InstitutionMembership.objects.select_related("institution", "user").get(id=source_identifier)
        except (InstitutionMembership.DoesNotExist, ValueError, ValidationError):
            return EvidenceSourceResolution(
                exists=False,
                source_domain=source_domain,
                source_type=source_type,
                source_identifier=source_identifier,
                source_revision="",
                learner_id=None,
                tenant_id=None,
                authority_class=EvidenceAuthorityClass.INSTITUTIONAL,
                reason_code="SOURCE_NOT_FOUND",
            )
        return EvidenceSourceResolution(
            exists=True,
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=str(membership.id),
            source_revision=f"membership:{membership.updated_at.isoformat()}",
            learner_id=str(membership.user_id),
            tenant_id=str(membership.institution_id),
            authority_class=EvidenceAuthorityClass.INSTITUTIONAL,
            observed_at=membership.updated_at,
            valid_from=None,
            valid_until=None,
            is_active=membership.is_active and membership.institution.is_active and membership.user.is_active,
            is_deleted=False,
            is_revoked=not membership.is_active,
            is_authoritative=True,
            safe_summary="Confirmed by institutional membership",
            summary_visibility=AttributeVisibility.AUTHORIZED_STAFF,
        )


class SelfStudyOnboardingContextResolver:
    def resolve(self, *, source_domain: str, source_type: str, source_identifier: str, learner_id, tenant_id) -> EvidenceSourceResolution:
        try:
            onboarding_id, revision = source_identifier.split(":", 1)
            onboarding = SelfStudyOnboarding.objects.select_related("workspace").get(id=onboarding_id)
        except (SelfStudyOnboarding.DoesNotExist, ValueError, ValidationError):
            return EvidenceSourceResolution(
                exists=False,
                source_domain=source_domain,
                source_type=source_type,
                source_identifier=source_identifier,
                source_revision="",
                learner_id=None,
                tenant_id=None,
                authority_class=EvidenceAuthorityClass.DECLARATIVE,
                reason_code="SOURCE_NOT_FOUND",
            )
        expected_revision = str(onboarding.version)
        is_active = (
            onboarding.status == SelfStudyOnboardingStatus.COMPLETED
            and onboarding.completed_at is not None
            and revision == expected_revision
        )
        return EvidenceSourceResolution(
            exists=True,
            source_domain=source_domain,
            source_type=source_type,
            source_identifier=f"{onboarding.id}:{revision}",
            source_revision=f"onboarding:{revision}",
            learner_id=str(onboarding.learner_id),
            tenant_id=str(onboarding.tenant_id),
            authority_class=EvidenceAuthorityClass.DECLARATIVE,
            observed_at=onboarding.completed_at,
            is_active=is_active,
            is_revoked=onboarding.status != SelfStudyOnboardingStatus.COMPLETED,
            is_authoritative=False,
            safe_summary="Declared during conversational onboarding",
            summary_visibility=AttributeVisibility.LEARNER_VISIBLE,
            reason_code="" if is_active else "SOURCE_STALE",
        )


def build_default_evidence_resolver_registry() -> EvidenceSourceResolverRegistry:
    registry = EvidenceSourceResolverRegistry()
    registry.register(
        source_domain=EvidenceSourceDomain.LEARNING_IDENTITY,
        source_type=EvidenceSourceType.LEARNER_DECLARATION,
        resolver=LearningIdentityDeclarationResolver(),
    )
    registry.register(
        source_domain=EvidenceSourceDomain.INSTITUTION,
        source_type=EvidenceSourceType.INSTITUTIONAL_MEMBERSHIP,
        resolver=InstitutionalMembershipResolver(),
    )
    registry.register(
        source_domain=EvidenceSourceDomain.SELF_STUDY,
        source_type=EvidenceSourceType.ONBOARDING_CONTEXT,
        resolver=SelfStudyOnboardingContextResolver(),
    )
    return registry
