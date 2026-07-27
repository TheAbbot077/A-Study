from __future__ import annotations

from django.core.exceptions import ValidationError

from apps.self_study.onboarding_models import SelfStudyOnboarding, SelfStudyOnboardingStatus

from ..application.onboarding_dto import ConfirmedLearningIdentityDeclaration, ConfirmedLearningIdentityDeclarationSet
from ..domain.enums import OnboardingDeclarationDisposition


class SelfStudyConfirmedOnboardingDeclarationResolver:
    source_schema_version = 1

    def resolve_confirmed_declarations(
        self,
        *,
        onboarding_session_id,
        onboarding_revision: int,
        tenant_id,
        learner_id,
    ) -> ConfirmedLearningIdentityDeclarationSet:
        try:
            onboarding = SelfStudyOnboarding.objects.select_related("tenant", "learner", "workspace").get(id=onboarding_session_id)
        except (SelfStudyOnboarding.DoesNotExist, ValueError, ValidationError) as exc:
            raise ValidationError("Onboarding source was not found.", code="ONBOARDING_SOURCE_NOT_FOUND") from exc
        if str(onboarding.tenant_id) != str(tenant_id):
            raise ValidationError("Onboarding source tenant mismatch.", code="TENANT_MISMATCH")
        if str(onboarding.learner_id) != str(learner_id):
            raise ValidationError("Onboarding source learner mismatch.", code="LEARNER_MISMATCH")
        if onboarding.version != onboarding_revision:
            raise ValidationError("Onboarding revision is unavailable.", code="ONBOARDING_REVISION_UNAVAILABLE")
        if onboarding.status != SelfStudyOnboardingStatus.COMPLETED or onboarding.completed_at is None:
            raise ValidationError("Onboarding is not completed.", code="ONBOARDING_NOT_COMPLETED")

        declarations: list[ConfirmedLearningIdentityDeclaration] = []
        confirmed_at = onboarding.completed_at
        for source_field, value in (
            ("topic_query", onboarding.topic_query),
            ("qualification_query", onboarding.qualification_query),
            ("target_date", onboarding.target_date.isoformat() if onboarding.target_date_known and onboarding.target_date else None),
            ("weekly_study_minutes", onboarding.weekly_study_minutes),
        ):
            if value in (None, ""):
                continue
            declarations.append(
                ConfirmedLearningIdentityDeclaration(
                    source_field=source_field,
                    raw_normalized_value=value,
                    source_value_schema_version=self.source_schema_version,
                    confirmation_disposition=OnboardingDeclarationDisposition.EXPLICITLY_CONFIRMED,
                    declared_at=confirmed_at,
                    confirmed_at=confirmed_at,
                    source_metadata={"workspace_id": str(onboarding.workspace_id)},
                )
            )

        return ConfirmedLearningIdentityDeclarationSet(
            onboarding_session_id=str(onboarding.id),
            onboarding_revision=onboarding.version,
            tenant_id=str(onboarding.tenant_id),
            learner_id=str(onboarding.learner_id),
            confirmed_at=confirmed_at,
            confirmed_by=str(onboarding.learner_id),
            source_event_id=f"self_study.onboarding.completed:{onboarding.id}:{onboarding.version}",
            declarations=tuple(declarations),
            source_status=onboarding.status,
            source_completed_at=confirmed_at,
            source_schema_version=self.source_schema_version,
        )
