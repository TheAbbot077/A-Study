from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from apps.remediation.domain.models import RemediationPlan
from apps.remediation.domain.repositories import ActivityRepository, OutcomeRepository, RemediationPlanRepository
from apps.remediation.infrastructure.persistence.repositories import (
    DjangoActivityRepository,
    DjangoOutcomeRepository,
    DjangoRemediationPlanRepository,
)
from apps.users.domain.models import User


@dataclass(frozen=True)
class RemediationTimelineEntry:
    event_type: str
    occurred_at: object
    label: str
    metadata: dict


class RemediationHistoryService:
    def __init__(
        self,
        plan_repository: Optional[RemediationPlanRepository] = None,
        activity_repository: Optional[ActivityRepository] = None,
        outcome_repository: Optional[OutcomeRepository] = None,
    ) -> None:
        self.plan_repository = plan_repository or DjangoRemediationPlanRepository()
        self.activity_repository = activity_repository or DjangoActivityRepository()
        self.outcome_repository = outcome_repository or DjangoOutcomeRepository()

    def list_learner_plans(self, learner: User) -> list[RemediationPlan]:
        return self.plan_repository.list_for_learner(learner)

    def timeline_for_plan(self, plan: RemediationPlan) -> list[RemediationTimelineEntry]:
        entries = [
            RemediationTimelineEntry(
                event_type="plan_created",
                occurred_at=plan.created_at,
                label="Remediation plan created",
                metadata={"status": plan.status},
            )
        ]
        for activity in self.activity_repository.list_for_plan(plan):
            entries.append(
                RemediationTimelineEntry(
                    event_type="activity_created",
                    occurred_at=activity.created_at,
                    label=activity.title,
                    metadata={"activity_type": activity.activity_type, "status": activity.status},
                )
            )
        for outcome in self.outcome_repository.list_for_plan(plan):
            entries.append(
                RemediationTimelineEntry(
                    event_type="outcome_recorded",
                    occurred_at=outcome.recorded_at,
                    label=outcome.outcome,
                    metadata={"notes": outcome.notes},
                )
            )
        return sorted(entries, key=lambda entry: entry.occurred_at)
