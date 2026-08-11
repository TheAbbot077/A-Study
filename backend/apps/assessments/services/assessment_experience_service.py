from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.assessments.domain.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentDeliverySession,
    AssessmentEvaluation,
    AssessmentExperience,
    AssessmentExperienceState,
    AssessmentPurpose,
    AssessmentResult,
    AssessmentState,
)
from apps.assessments.services.assessment_delivery_service import AssessmentDeliveryService
from apps.assessments.services.assessment_evaluation_service import AssessmentEvaluationService
from apps.assessments.services.assessment_environment_service import AssessmentEnvironmentService
from apps.assessments.services.assessment_service import AssessmentService
from apps.assessments.services.evidence_integration_service import EvidenceIntegrationService
from apps.assessments.services.mastery_service import MasteryService
from apps.core.exceptions import DomainValidationError, LifecycleTransitionError
from apps.core.events import BusinessEvent, EventPublisher


class AssessmentExperienceService:
    def __init__(self, event_publisher: EventPublisher | None = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()
        self.assessment_service = AssessmentService(event_publisher=self.event_publisher)
        self.delivery_service = AssessmentDeliveryService(event_publisher=self.event_publisher)
        self.evaluation_service = AssessmentEvaluationService(event_publisher=self.event_publisher)
        self.evidence_integration_service = EvidenceIntegrationService(event_publisher=self.event_publisher)
        self.mastery_service = MasteryService(event_publisher=self.event_publisher)
        self.environment_service = AssessmentEnvironmentService()

    @transaction.atomic
    def create_experience(
        self,
        *,
        learner,
        assessment: Assessment,
        purpose: str,
        learning_journey_id=None,
        institution_id=None,
        policy_version: str = "1",
        policy_snapshot: dict | None = None,
        attempt_number: int = 1,
        previous_experience: AssessmentExperience | None = None,
    ) -> AssessmentExperience:
        if purpose not in AssessmentPurpose.values:
            raise DomainValidationError(f"Unsupported assessment purpose: {purpose}.")
        experience = AssessmentExperience.objects.create(
            learner=learner,
            learning_journey_id=learning_journey_id,
            institution_id=institution_id,
            content_concept=assessment.content_concept,
            purpose=purpose,
            assessment=assessment,
            assessment_strategy_type=str(assessment.metadata.get("strategy_type", "")) if isinstance(assessment.metadata, dict) else "",
            policy_version=policy_version,
            policy_snapshot=policy_snapshot or {},
            environment_policy_version=policy_version,
            environment_policy_checksum=(policy_snapshot or {}).get("source_checksum", ""),
            attempt_number=attempt_number,
            previous_experience=previous_experience,
            state=AssessmentExperienceState.CREATED,
            current_step={"code": "ASSESSMENT_CREATED", "title": "Assessment prepared"},
            blockers=[],
        )
        self._emit("assessment.experience_created", experience)
        return experience

    @transaction.atomic
    def prepare_experience(self, experience: AssessmentExperience) -> AssessmentExperience:
        self._ensure_owned(experience)
        experience.set_state(AssessmentExperienceState.READY)
        experience.save()
        self._emit("assessment.experience_ready", experience)
        return experience

    @transaction.atomic
    def start_experience(self, experience: AssessmentExperience) -> AssessmentExperience:
        self._ensure_owned(experience)
        if experience.state not in {AssessmentExperienceState.CREATED, AssessmentExperienceState.READY}:
            raise LifecycleTransitionError(f"Cannot start assessment experience from {experience.state}.")
        if experience.assessment_attempt is None:
            attempt = self.assessment_service.start_attempt(experience.assessment, experience.learner, metadata={"experience_id": str(experience.id), "purpose": experience.purpose})
            experience.assessment_attempt = attempt
        delivery_session = AssessmentDeliverySession.objects.filter(assessment_attempt=experience.assessment_attempt).first()
        if delivery_session is None:
            delivery_session = self.delivery_service.create_delivery_session(experience.assessment, experience.learner)
        delivery_session = self.delivery_service.start_delivery_session(delivery_session)
        experience.delivery_session = delivery_session
        experience.set_state(AssessmentExperienceState.AWAITING_RESPONSE)
        experience.current_step = {"code": "RESPOND", "title": "Answer the question"}
        experience.blockers = []
        experience.save()
        self._emit("assessment.experience_started", experience)
        return experience

    @transaction.atomic
    def submit_response(self, experience: AssessmentExperience, *, item_id, response_data: dict) -> AssessmentExperience:
        self._ensure_owned(experience)
        if experience.assessment_attempt is None or experience.delivery_session is None:
            raise LifecycleTransitionError("Assessment experience is not ready for submission.")
        if experience.state not in {AssessmentExperienceState.AWAITING_RESPONSE, AssessmentExperienceState.IN_PROGRESS}:
            raise LifecycleTransitionError(f"Cannot submit assessment response from {experience.state}.")
        response = self.assessment_service.submit_response(
            experience.assessment_attempt,
            next(item for item in experience.assessment.items.all() if str(item.id) == str(item_id)),
            response_data,
            metadata={"experience_id": str(experience.id)},
        )
        experience.set_state(AssessmentExperienceState.SUBMITTED)
        experience.submitted_at = experience.submitted_at or response.submitted_at
        experience.current_step = {"code": "EVALUATE", "title": "Evaluate response"}
        experience.save()
        self._emit("assessment.experience_submitted", experience)
        return experience

    @transaction.atomic
    def evaluate_experience(self, experience: AssessmentExperience) -> AssessmentExperience:
        self._ensure_owned(experience)
        if experience.assessment_attempt is None:
            raise LifecycleTransitionError("Assessment experience has no attempt.")
        if experience.state not in {AssessmentExperienceState.SUBMITTED, AssessmentExperienceState.AWAITING_RESPONSE}:
            raise LifecycleTransitionError(f"Cannot evaluate assessment experience from {experience.state}.")
        experience.set_state(AssessmentExperienceState.EVALUATING)
        experience.save()
        result = self.evaluation_service.evaluate_attempt(experience.assessment_attempt)
        experience.evaluation = AssessmentEvaluation.objects.filter(response__attempt=experience.assessment_attempt).order_by("-created_at").first()
        experience.feedback_available = True
        experience.set_state(AssessmentExperienceState.EVALUATED)
        experience.save()
        self.evidence_integration_service.integrate_completed_attempt(experience.assessment_attempt)
        self.mastery_service.evaluate_mastery(experience.learner, experience.content_concept)
        self.assessment_service.complete_attempt(experience.assessment_attempt)
        if experience.delivery_session:
            self.delivery_service.complete_delivery_session(experience.delivery_session)
        experience.set_state(AssessmentExperienceState.COMPLETED)
        experience.current_step = {"code": "CONTINUE_JOURNEY", "title": "Continue your journey"}
        experience.save()
        self._emit("assessment.experience_completed", experience)
        return experience

    def get_product_state(self, experience: AssessmentExperience) -> dict:
        action = self.resolve_available_actions(experience)
        return {
            "experience_id": str(experience.id),
            "purpose": experience.purpose,
            "status": experience.state.upper(),
            "current_step": experience.current_step or {"code": "START", "title": "Start assessment"},
            "available_actions": action["actions"],
            "blockers": experience.blockers,
            "attempt": {"number": experience.attempt_number},
            "feedback_available": experience.feedback_available,
            "tool_policy": self.environment_service.resolve_policy(experience),
            "environment": self.environment_service.resolve_policy(experience),
        }

    def resolve_available_actions(self, experience: AssessmentExperience) -> dict:
        environment = self.environment_service.resolve_policy(experience)
        actions = ["START"] if experience.state in {AssessmentExperienceState.CREATED, AssessmentExperienceState.READY} else []
        if experience.state == AssessmentExperienceState.AWAITING_RESPONSE:
            actions = ["SUBMIT_RESPONSE", "CANCEL"]
        elif experience.state == AssessmentExperienceState.SUBMITTED:
            actions = ["VIEW_FEEDBACK"]
        elif experience.state == AssessmentExperienceState.EVALUATED:
            actions = ["CONTINUE_JOURNEY", "RETRY"]
        elif experience.state in {AssessmentExperienceState.COMPLETED, AssessmentExperienceState.CANCELLED, AssessmentExperienceState.EXPIRED, AssessmentExperienceState.FAILED}:
            actions = ["CONTINUE_JOURNEY"]
        blockers = list(experience.blockers or [])
        for blocker in environment["blockers"]:
            blockers.append(blocker["reason_code"])
        return {"actions": actions, "blockers": blockers, "environment": environment}

    @transaction.atomic
    def synchronize_experience(self, experience: AssessmentExperience) -> AssessmentExperience:
        self._ensure_owned(experience)
        if experience.assessment_attempt_id:
            attempt = experience.assessment_attempt
            if attempt.state == AssessmentState.SUBMITTED and experience.state not in {AssessmentExperienceState.SUBMITTED, AssessmentExperienceState.EVALUATING, AssessmentExperienceState.EVALUATED, AssessmentExperienceState.COMPLETED}:
                experience.set_state(AssessmentExperienceState.SUBMITTED)
            if attempt.state == AssessmentState.EVALUATED and experience.state not in {AssessmentExperienceState.EVALUATED, AssessmentExperienceState.COMPLETED}:
                experience.set_state(AssessmentExperienceState.EVALUATED)
            if attempt.state == AssessmentState.COMPLETED and experience.state != AssessmentExperienceState.COMPLETED:
                experience.set_state(AssessmentExperienceState.COMPLETED)
        experience.save()
        self._emit("assessment.experience_synchronized", experience)
        return experience

    def _ensure_owned(self, experience: AssessmentExperience) -> None:
        if experience.learner_id is None:
            raise DomainValidationError("Assessment experience must belong to a learner.")

    def _emit(self, event_name: str, experience: AssessmentExperience) -> None:
        self.event_publisher.publish(
            BusinessEvent.create(
                event_name,
                payload={
                    "experience_id": str(experience.id),
                    "assessment_id": str(experience.assessment_id),
                    "learner_id": str(experience.learner_id),
                    "purpose": experience.purpose,
                    "state": experience.state,
                },
            )
        )
