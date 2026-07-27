from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ConfirmedLearningIdentityDeclaration:
    source_field: str
    raw_normalized_value: Any
    source_value_schema_version: int
    confirmation_disposition: str
    declared_at: datetime | None = None
    confirmed_at: datetime | None = None
    explicit_clear: bool = False
    visibility_hint: str = ""
    restriction_hint: str = ""
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfirmedLearningIdentityDeclarationSet:
    onboarding_session_id: str
    onboarding_revision: int
    tenant_id: str
    learner_id: str
    confirmed_at: datetime
    confirmed_by: str
    source_event_id: str
    declarations: tuple[ConfirmedLearningIdentityDeclaration, ...]
    source_status: str
    source_completed_at: datetime
    source_schema_version: int = 1
