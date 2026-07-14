from __future__ import annotations

from apps.assessments.domain.models import LearningEvidence, LearningEvidenceType
from apps.remediation.domain.models import (
    DomainRemediationActivity,
    DomainRemediationPlan,
    DomainRemediationRecommendation,
)
from apps.remediation.models import (
    RemediationActivity,
    RemediationAttempt,
    RemediationOutcome,
    RemediationPlan,
    RemediationRecommendation,
)
from apps.users.domain.models import User

ORMRemediationPlan = RemediationPlan
ORMRemediationRecommendation = RemediationRecommendation
ORMRemediationActivity = RemediationActivity


class DjangoRemediationPlanRepository:
    def add(self, plan: DomainRemediationPlan | ORMRemediationPlan) -> ORMRemediationPlan:
        if isinstance(plan, DomainRemediationPlan):
            orm_plan = ORMRemediationPlan.objects.create(
                learner=plan.learner,
                content_concept=plan.content_concept,
                trigger_evidence=plan.trigger_evidence if isinstance(plan.trigger_evidence, LearningEvidence) else None,
                status=plan.status,
                rationale=plan.rationale,
                metadata=plan.metadata,
            )
            return orm_plan
        plan.save()
        return plan

    def save(self, plan: DomainRemediationPlan | ORMRemediationPlan) -> DomainRemediationPlan | ORMRemediationPlan:
        plan.save()
        return plan

    def get(self, plan_id: str) -> ORMRemediationPlan:
        return ORMRemediationPlan.objects.get(id=plan_id)

    def list_for_learner(self, learner: User) -> list[ORMRemediationPlan]:
        return list(ORMRemediationPlan.objects.filter(learner=learner).order_by("-created_at"))

    def list_by_status(self, status: str) -> list[ORMRemediationPlan]:
        return list(ORMRemediationPlan.objects.filter(status=status).order_by("-created_at"))


class DjangoRecommendationRepository:
    def add(self, recommendation: DomainRemediationRecommendation | ORMRemediationRecommendation) -> ORMRemediationRecommendation:
        if isinstance(recommendation, DomainRemediationRecommendation):
            orm_recommendation = ORMRemediationRecommendation.objects.create(
                plan=recommendation.plan,
                recommendation_type=recommendation.recommendation_type,
                title=recommendation.title,
                rationale=recommendation.rationale,
                priority=recommendation.priority,
                metadata=recommendation.metadata,
            )
            return orm_recommendation
        recommendation.save()
        return recommendation

    def list_for_plan(self, plan: ORMRemediationPlan) -> list[ORMRemediationRecommendation]:
        return list(ORMRemediationRecommendation.objects.filter(plan=plan).order_by("priority", "created_at"))


class DjangoActivityRepository:
    def add(self, activity: DomainRemediationActivity | ORMRemediationActivity) -> ORMRemediationActivity:
        if isinstance(activity, DomainRemediationActivity):
            orm_activity = ORMRemediationActivity.objects.create(
                plan=activity.plan,
                recommendation=activity.recommendation if isinstance(activity.recommendation, ORMRemediationRecommendation) else None,
                activity_type=activity.activity_type,
                title=activity.title,
                instructions=activity.instructions,
                status=activity.status,
                evidence_producer_type=activity.evidence_producer_type,
                evidence_reference_id=activity.evidence_reference_id,
                metadata=activity.metadata,
            )
            return orm_activity
        activity.save()
        return activity

    def save(self, activity: ORMRemediationActivity) -> ORMRemediationActivity:
        activity.save()
        return activity

    def list_for_plan(self, plan: ORMRemediationPlan) -> list[ORMRemediationActivity]:
        return list(ORMRemediationActivity.objects.filter(plan=plan).order_by("created_at"))


class DjangoAttemptRepository:
    def add(self, attempt: RemediationAttempt) -> RemediationAttempt:
        attempt.save()
        return attempt

    def save(self, attempt: RemediationAttempt) -> RemediationAttempt:
        attempt.save()
        return attempt

    def list_for_activity(self, activity: ORMRemediationActivity) -> list[RemediationAttempt]:
        return list(RemediationAttempt.objects.filter(activity=activity).order_by("-created_at"))


class DjangoOutcomeRepository:
    def add(self, outcome: RemediationOutcome) -> RemediationOutcome:
        outcome.save()
        return outcome

    def list_for_plan(self, plan: ORMRemediationPlan) -> list[RemediationOutcome]:
        return list(RemediationOutcome.objects.filter(plan=plan).order_by("-recorded_at"))


class DjangoEvidenceRepository:
    NEGATIVE_EVIDENCE_TYPES = {
        LearningEvidenceType.MISCONCEPTION,
        LearningEvidenceType.PARTIAL_UNDERSTANDING,
    }

    def list_for_learner(self, learner: User) -> list[LearningEvidence]:
        return list(LearningEvidence.objects.filter(learner=learner).order_by("-created_at"))

    def list_remediation_candidates_for_learner(self, learner: User) -> list[LearningEvidence]:
        return list(
            LearningEvidence.objects.filter(learner=learner, evidence_type__in=self.NEGATIVE_EVIDENCE_TYPES).order_by("-created_at")
        )


__all__ = [
    "DjangoRemediationPlanRepository",
    "DjangoRecommendationRepository",
    "DjangoActivityRepository",
    "DjangoAttemptRepository",
    "DjangoOutcomeRepository",
    "DjangoEvidenceRepository",
]
