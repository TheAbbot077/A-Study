from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class EvidenceSourceResolution:
    exists: bool
    source_domain: str
    source_type: str
    source_identifier: str
    source_revision: str
    learner_id: str | None
    tenant_id: str | None
    authority_class: str
    observed_at: datetime | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    is_active: bool = False
    is_revoked: bool = False
    is_deleted: bool = False
    is_authoritative: bool = False
    safe_summary: str = ""
    summary_visibility: str = "AUTHORIZED_STAFF"
    reason_code: str = ""


class LearningIdentityEvidenceSourceResolver(Protocol):
    def resolve(
        self,
        *,
        source_domain: str,
        source_type: str,
        source_identifier: str,
        learner_id,
        tenant_id,
    ) -> EvidenceSourceResolution:
        ...


@dataclass(frozen=True)
class ObservationSourceEnvelope:
    exists: bool
    tenant_id: str | None
    learner_id: str | None
    source_domain: str
    source_type: str
    source_identifier: str
    source_revision: str
    occurred_at: datetime | None
    observation_type: str
    authority_class: str
    lifecycle_state: str = "ACTIVE"
    controlled_payload: dict | None = None
    learner_safe_title: str = ""
    learner_safe_summary: str = ""
    reason_code: str = ""


class LearningIdentityObservationSourceResolver(Protocol):
    def resolve(
        self,
        *,
        source_domain: str,
        source_type: str,
        source_identifier: str,
        learner_id,
        tenant_id,
    ) -> ObservationSourceEnvelope:
        ...
