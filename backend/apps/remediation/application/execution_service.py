from __future__ import annotations

from typing import Optional

from apps.assessments.domain.models import LearningEvidence
from apps.core.events import BusinessEvent, EventPublisher
from apps.remediation.domain.models import (
    RemediationActivity,
    RemediationAttempt,
    RemediationOutcome,
    RemediationOutcomeValue,
    RemediationPlan,
)
from apps.remediation.domain.repositories import ActivityRepository, AttemptRepository, OutcomeRepository, RemediationPlanRepository
from apps.remediation.infrastructure.persistence.repositories import (
    DjangoActivityRepository,
    DjangoAttemptRepository,
    DjangoOutcomeRepository,
    DjangoRemediationPlanRepository,
)


class RemediationExecutionService:
    def __init__(
        self,
        plan_repository: Optional[RemediationPlanRepository] = None,
        activity_repository: Optional[ActivityRepository] = None,
        attempt_repository: Optional[AttemptRepository] = None,
        outcome_repository: Optional[OutcomeRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.plan_repository = plan_repository or DjangoRemediationPlanRepository()
        self.activity_repository = activity_repository or DjangoActivityRepository()
        self.attempt_repository = attempt_repository or DjangoAttemptRepository()
        self.outcome_repository = outcome_repository or DjangoOutcomeRepository()
        self.event_publisher = event_publisher or EventPublisher()

    def start_remediation(self, plan: RemediationPlan) -> RemediationPlan:
        plan.activate()
        plan = self.plan_repository.save(plan)
        self._publish_plan_event("remediation.started", plan)
        return plan

    def complete_remediation(self, plan: RemediationPlan) -> RemediationPlan:
        plan.complete()
        plan = self.plan_repository.save(plan)
        self._publish_plan_event("remediation.completed", plan)
        return plan

    def escalate_remediation(self, plan: RemediationPlan) -> RemediationPlan:
        plan.escalate()
        plan = self.plan_repository.save(plan)
        self._publish_plan_event("remediation.escalated", plan)
        return plan

    def cancel_remediation(self, plan: RemediationPlan) -> RemediationPlan:
        plan.cancel()
        plan = self.plan_repository.save(plan)
        self._publish_plan_event("remediation.cancelled", plan)
        return plan

    def close_remediation(self, plan: RemediationPlan) -> RemediationPlan:
        plan.close()
        plan = self.plan_repository.save(plan)
        self._publish_plan_event("remediation.closed", plan)
        return plan

    def start_activity(self, activity: RemediationActivity) -> RemediationActivity:
        activity.start()
        return self.activity_repository.save(activity)

    def complete_activity(self, activity: RemediationActivity, evidence_reference_id: str = "") -> RemediationActivity:
        activity.complete(evidence_reference_id=evidence_reference_id)
        return self.activity_repository.save(activity)

    def start_activity_attempt(self, activity: RemediationActivity) -> RemediationAttempt:
        attempt = RemediationAttempt(activity=activity, learner=activity.plan.learner)
        return self.attempt_repository.add(attempt)

    def complete_activity_attempt(self, attempt: RemediationAttempt) -> RemediationAttempt:
        attempt.complete()
        return self.attempt_repository.save(attempt)

    def record_outcome(
        self,
        plan: RemediationPlan,
        outcome: str,
        activity: RemediationActivity | None = None,
        supporting_evidence: LearningEvidence | None = None,
        notes: str = "",
        metadata: dict | None = None,
    ) -> RemediationOutcome:
        remediation_outcome = RemediationOutcome(
            plan=plan,
            activity=activity,
            supporting_evidence=supporting_evidence,
            outcome=outcome,
            notes=notes,
            metadata=metadata or {},
        )
        remediation_outcome = self.outcome_repository.add(remediation_outcome)
        if remediation_outcome.outcome == RemediationOutcomeValue.ESCALATED:
            self.escalate_remediation(plan)
        return remediation_outcome

    def _publish_plan_event(self, event_name: str, plan: RemediationPlan) -> None:
        self.event_publisher.publish(
            BusinessEvent.create(
                event_name,
                payload={
                    "remediation_plan_id": str(plan.id),
                    "learner_id": str(plan.learner_id),
                    "content_concept_id": str(plan.content_concept_id),
                    "status": plan.status,
                },
            )
        )
