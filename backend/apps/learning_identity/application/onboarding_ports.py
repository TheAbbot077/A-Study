from __future__ import annotations

from typing import Protocol

from .onboarding_dto import ConfirmedLearningIdentityDeclarationSet


class ConfirmedOnboardingDeclarationSource(Protocol):
    def resolve_confirmed_declarations(
        self,
        *,
        onboarding_session_id,
        onboarding_revision: int,
        tenant_id,
        learner_id,
    ) -> ConfirmedLearningIdentityDeclarationSet:
        ...
