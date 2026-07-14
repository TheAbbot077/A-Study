from __future__ import annotations

from typing import Optional

from apps.assessments.domain.models import LearningEvidence, LearningEvidenceType
from apps.core.events import BusinessEvent, EventPublisher
from apps.remediation.application.recommendation_service import RecommendationService
from apps.remediation.domain.models import (
    DomainRemediationActivity as RemediationActivity,
    DomainRemediationPlan as RemediationPlan,
    DomainRemediationRecommendation as RemediationRecommendation,
    RemediationActivityType,
    RemediationPlanStatus,
    RemediationRecommendationType,
)
from apps.remediation.domain.repositories import ActivityRepository, RecommendationRepository, RemediationPlanRepository
from apps.remediation.infrastructure.persistence.repositories import (
    DjangoActivityRepository,
    DjangoRecommendationRepository,
    DjangoRemediationPlanRepository,
)


class RemediationPlanningService:
    REMEDIATION_EVIDENCE_TYPES = {
        LearningEvidenceType.MISCONCEPTION,
        LearningEvidenceType.PARTIAL_UNDERSTANDING,
    }

    def __init__(
        self,
        plan_repository: Optional[RemediationPlanRepository] = None,
        recommendation_repository: Optional[RecommendationRepository] = None,
        activity_repository: Optional[ActivityRepository] = None,
        recommendation_service: Optional[RecommendationService] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.plan_repository = plan_repository or DjangoRemediationPlanRepository()
        self.recommendation_repository = recommendation_repository or DjangoRecommendationRepository()
        self.activity_repository = activity_repository or DjangoActivityRepository()
        self.recommendation_service = recommendation_service or RecommendationService()
        self.event_publisher = event_publisher or EventPublisher()

    def remediation_required(self, evidence: LearningEvidence) -> bool:
        return evidence.evidence_type in self.REMEDIATION_EVIDENCE_TYPES or evidence.confidence < 0.5

    def plan_from_evidence(self, evidence: LearningEvidence) -> RemediationPlan | None:
        if not self.remediation_required(evidence):
            return None

        plan = RemediationPlan(
            learner=evidence.learner,
            content_concept=evidence.content_concept,
            trigger_evidence=evidence,
            status=RemediationPlanStatus.PENDING,
            rationale=f"Remediation required from evidence type {evidence.evidence_type}.",
            metadata={
                "source_type": evidence.source_type,
                "source_id": evidence.source_id,
                "evidence_type": evidence.evidence_type,
            },
        )
        plan = self.plan_repository.add(plan)
        recommendations = self.assign_recommendations(plan, evidence)
        self.event_publisher.publish(
            BusinessEvent.create(
                "remediation.planned",
                payload={
                    "remediation_plan_id": str(plan.id),
                    "learner_id": str(plan.learner_id),
                    "content_concept_id": str(plan.content_concept_id),
                    "trigger_evidence_id": str(evidence.id),
                    "recommendation_count": len(recommendations),
                },
            )
        )
        return plan

    def assign_recommendations(self, plan: RemediationPlan, evidence: LearningEvidence) -> list[RemediationRecommendation]:
        recommendations: list[RemediationRecommendation] = []
        for draft in self.recommendation_service.recommendations_for_evidence(evidence):
            recommendation = RemediationRecommendation(
                plan=plan,
                recommendation_type=draft.recommendation_type,
                title=draft.title,
                rationale=draft.rationale,
                priority=draft.priority,
                metadata=draft.metadata,
            )
            recommendation = self.recommendation_repository.add(recommendation)
            recommendations.append(recommendation)
            self.create_activity_for_recommendation(plan, recommendation)
        return recommendations

    def create_activity_for_recommendation(
        self,
        plan: RemediationPlan,
        recommendation: RemediationRecommendation,
    ) -> RemediationActivity:
        activity = RemediationActivity(
            plan=plan,
            recommendation=recommendation,
            activity_type=self._activity_type_for(recommendation.recommendation_type),
            title=recommendation.title,
            instructions=recommendation.rationale,
            evidence_producer_type="remediation_activity",
            metadata={"recommendation_type": recommendation.recommendation_type},
        )
        return self.activity_repository.add(activity)

    def _activity_type_for(self, recommendation_type: str) -> str:
        mapping = {
            RemediationRecommendationType.REVIEW_LESSON: RemediationActivityType.LESSON_REPLAY,
            RemediationRecommendationType.REPEAT_ACTIVITY: RemediationActivityType.PRACTICE_ASSESSMENT,
            RemediationRecommendationType.TEACH_ARIEL: RemediationActivityType.TEACH_ARIEL,
            RemediationRecommendationType.ADDITIONAL_QUESTIONS: RemediationActivityType.PRACTICE_ASSESSMENT,
            RemediationRecommendationType.READ_SOURCE_MATERIAL: RemediationActivityType.LESSON_REPLAY,
            RemediationRecommendationType.SIMULATION: RemediationActivityType.SIMULATION,
            RemediationRecommendationType.EDUCATOR_REVIEW: RemediationActivityType.EDUCATOR_REVIEW,
            RemediationRecommendationType.PROGRAMMING_TASK: RemediationActivityType.PROGRAMMING_TASK,
        }
        return mapping.get(recommendation_type, RemediationActivityType.CUSTOM)
