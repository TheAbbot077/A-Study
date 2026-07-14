from __future__ import annotations

from apps.assessments.domain.models import LearningEvidence
from apps.core.events import BusinessEvent
from apps.remediation.application import RemediationPlanningService


class EvidenceIntegratedConsumer:
    def __init__(self, planning_service: RemediationPlanningService | None = None) -> None:
        self.planning_service = planning_service or RemediationPlanningService()

    def handle(self, event: BusinessEvent) -> None:
        evidence_id = event.payload.get("learning_evidence_id")
        if not evidence_id:
            return
        evidence = LearningEvidence.objects.get(id=evidence_id)
        self.planning_service.plan_from_evidence(evidence)
