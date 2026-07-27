from __future__ import annotations

from ..domain.enums import AttributeSourceType, AttributeVisibility
from ..domain.models import LearnerLearningProfile, LearningIdentityAttribute, LearningIdentityDeclarationSynchronization
from .services import _ensure_actor_can_manage, _ensure_profile_access, _has_staff_authority


class GetOnboardingDeclarationSynchronizationStatus:
    def execute(self, *, onboarding_session_id, onboarding_revision: int, tenant_id, learner_id, actor):
        _ensure_actor_can_manage(actor=actor, tenant_id=tenant_id, learner_id=learner_id)
        receipt = LearningIdentityDeclarationSynchronization.objects.select_related("profile", "profile_version").get(
            onboarding_session_id=onboarding_session_id,
            onboarding_revision=onboarding_revision,
            tenant_id=tenant_id,
            learner_id=learner_id,
        )
        return {
            "id": str(receipt.id),
            "onboarding_session_id": str(receipt.onboarding_session_id),
            "onboarding_revision": receipt.onboarding_revision,
            "status": receipt.status,
            "result_code": receipt.result_code,
            "readiness_status": receipt.readiness_status,
            "profile_id": str(receipt.profile_id) if receipt.profile_id else None,
            "profile_version_id": str(receipt.profile_version_id) if receipt.profile_version_id else None,
            "profile_version_number": receipt.profile_version.version_number if receipt.profile_version_id else None,
            "applied_at": receipt.applied_at.isoformat() if receipt.applied_at else None,
            "blocked_at": receipt.blocked_at.isoformat() if receipt.blocked_at else None,
            "change_counts": receipt.change_counts,
            "reason_codes": receipt.reason_codes,
        }


class ListDeclaredLearningIdentityAttributes:
    def execute(self, *, profile_id, actor):
        profile = LearnerLearningProfile.objects.get(id=profile_id)
        _ensure_profile_access(actor=actor, profile=profile)
        if not profile.current_version_id:
            return []
        authorized_staff = _has_staff_authority(actor=actor, tenant_id=profile.tenant_id)
        attributes = LearningIdentityAttribute.objects.filter(
            profile_version=profile.current_version,
            classification="DECLARED",
        ).order_by("attribute_type", "created_at")
        result = []
        for attribute in attributes:
            if attribute.visibility in {AttributeVisibility.RESTRICTED, AttributeVisibility.SYSTEM_ONLY} and not authorized_staff and actor.id != profile.learner_id:
                continue
            result.append(
                {
                    "attribute_id": str(attribute.id),
                    "attribute_type": attribute.attribute_type,
                    "value": attribute.value if attribute.visibility == AttributeVisibility.LEARNER_VISIBLE or authorized_staff or actor.id == profile.learner_id else None,
                    "visibility": attribute.visibility,
                    "restricted": attribute.restricted,
                    "source_type": attribute.source_type,
                    "declared_at": attribute.declared_at.isoformat() if attribute.declared_at else None,
                    "needs_review": attribute.review_required,
                }
            )
        return result


class GetLearnerSafeDeclarationSummary:
    def execute(self, *, profile_id, actor):
        rows = ListDeclaredLearningIdentityAttributes().execute(profile_id=profile_id, actor=actor)
        safe = []
        for row in rows:
            if row["visibility"] in {AttributeVisibility.RESTRICTED, AttributeVisibility.SYSTEM_ONLY}:
                continue
            safe.append(
                {
                    "attribute_type": row["attribute_type"],
                    "value": row["value"],
                    "source_label": "You told us this during onboarding." if row["source_type"] == AttributeSourceType.ONBOARDING else "You declared this.",
                    "declared_at": row["declared_at"],
                    "needs_review": row["needs_review"],
                }
            )
        return safe
