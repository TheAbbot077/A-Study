from __future__ import annotations

from apps.core.events import EventPublisher

from ..application.declaration_services import ApplyConfirmedOnboardingDeclarationsService, PreviewOnboardingDeclarationChangesService
from .onboarding_resolver import SelfStudyConfirmedOnboardingDeclarationResolver


def build_onboarding_declaration_preview_service() -> PreviewOnboardingDeclarationChangesService:
    return PreviewOnboardingDeclarationChangesService(source=SelfStudyConfirmedOnboardingDeclarationResolver())


def build_onboarding_declaration_apply_service(*, events: EventPublisher | None = None) -> ApplyConfirmedOnboardingDeclarationsService:
    return ApplyConfirmedOnboardingDeclarationsService(
        source=SelfStudyConfirmedOnboardingDeclarationResolver(),
        events=events,
    )
