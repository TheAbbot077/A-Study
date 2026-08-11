from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.educational_organization.services.authorization_service import AuthorizationService

from ..domain.enums import ParticipationStatus, PreparednessAssignmentPopulationMode
from ..domain.models import (
    ArielPreparednessAttempt,
    ClassPreparednessAssignment,
    LessonPreparation,
    LearnerPreparednessParticipation,
    PreparednessActivity,
    PreparednessPrompt,
)
from ..domain.roster import UnavailableClassroomRosterProvider


class CreateLessonPreparationService:
    @staticmethod
    @transaction.atomic
    def execute(*, institution_id, teacher_id, teaching_assignment, course_offering, class_group, title, learning_objective, topic_reference="", lesson_date=None):
        return LessonPreparation.objects.create(
            institution_id=institution_id,
            teacher_id=teacher_id,
            teaching_assignment=teaching_assignment,
            course_offering=course_offering,
            class_group=class_group,
            title=title,
            learning_objective=learning_objective,
            topic_reference=topic_reference,
            lesson_date=lesson_date,
        )


class PublishLessonPreparationService:
    @staticmethod
    @transaction.atomic
    def execute(preparation: LessonPreparation):
        preparation.transition_to("published")
        preparation.save()
        return preparation


class AssignPreparednessService:
    @staticmethod
    @transaction.atomic
    def execute(
        *,
        activity,
        class_group,
        course_offering,
        institution,
        population_mode=PreparednessAssignmentPopulationMode.EXPLICIT_PARTICIPANTS,
        roster_provider=None,
    ):
        if population_mode == PreparednessAssignmentPopulationMode.CLASS_ROSTER:
            provider = roster_provider or UnavailableClassroomRosterProvider()
            try:
                provider.list_eligible_learners(
                    institution_id=institution.id,
                    class_group_id=class_group.id,
                    course_offering_id=course_offering.id,
                )
            except RuntimeError as exc:
                raise ValidationError("Roster authority is unavailable.", code="ROSTER_AUTHORITY_UNAVAILABLE") from exc
        return ClassPreparednessAssignment.objects.create(
            activity=activity,
            class_group=class_group,
            course_offering=course_offering,
            institution=institution,
            population_mode=population_mode,
            population_source="PREPAREDNESS_PARTICIPATION_RECORDS",
            published_at=timezone.now(),
        )


class AddLearnerPreparednessParticipantService:
    @staticmethod
    @transaction.atomic
    def execute(*, assignment: ClassPreparednessAssignment, learner=None, learner_id=None):
        if assignment.population_mode != PreparednessAssignmentPopulationMode.EXPLICIT_PARTICIPANTS:
            raise ValidationError("Population mode is unsupported.", code="PREPAREDNESS_POPULATION_MODE_UNSUPPORTED")
        if assignment.status in {"closed", "cancelled", "archived"}:
            raise ValidationError("Population is frozen.", code="PREPAREDNESS_POPULATION_FROZEN")
        if learner is None and learner_id is None:
            raise ValidationError("Participant is not eligible.", code="PREPAREDNESS_PARTICIPANT_NOT_ELIGIBLE")
        if learner is not None and learner_id is None:
            learner_id = learner.id
        participation, created = LearnerPreparednessParticipation.objects.get_or_create(
            assignment=assignment,
            learner_id=learner_id,
            defaults={"status": ParticipationStatus.ASSIGNED},
        )
        return participation, created


class RemoveLearnerPreparednessParticipantService:
    @staticmethod
    @transaction.atomic
    def execute(*, participation: LearnerPreparednessParticipation):
        if participation.status in {ParticipationStatus.RESPONDED, ParticipationStatus.COMPLETED}:
            raise ValidationError("Participant history cannot be deleted after activity begins.", code="PREPAREDNESS_POPULATION_FROZEN")
        participation.status = ParticipationStatus.DECLINED
        participation.version += 1
        participation.save(update_fields=["status", "version"])
        return participation


class StartLearnerPreparednessService:
    @staticmethod
    @transaction.atomic
    def execute(*, assignment: ClassPreparednessAssignment, learner):
        participation, _ = AddLearnerPreparednessParticipantService.execute(assignment=assignment, learner=learner)
        if participation.status == ParticipationStatus.ASSIGNED:
            participation.status = ParticipationStatus.OPEN
            participation.started_at = participation.started_at or timezone.now()
            participation.version += 1
            participation.save(update_fields=["status", "started_at", "version"])
        return participation


class PublishPreparednessActivityService:
    @staticmethod
    @transaction.atomic
    def execute(activity: PreparednessActivity):
        activity.transition_to("published")
        activity.save()
        return activity


class OpenPreparednessAssignmentService:
    @staticmethod
    @transaction.atomic
    def execute(assignment: ClassPreparednessAssignment):
        if assignment.status == "published":
            assignment.status = "open"
            assignment.published_at = assignment.published_at or timezone.now()
            assignment.version += 1
            assignment.save(update_fields=["status", "published_at", "version"])
        return assignment


class RespondToPreparednessService:
    @staticmethod
    @transaction.atomic
    def execute(*, participation: LearnerPreparednessParticipation, learner_id, response_text: str):
        if participation.learner_id != learner_id:
            raise ValidationError("Only the owning learner can respond.", code="LEARNER_PREPAREDNESS_ACCESS_DENIED")
        participation.transition_to(ParticipationStatus.RESPONDED)
        participation.save()
        return participation, response_text.strip()


class OptInArielPreparednessService:
    @staticmethod
    @transaction.atomic
    def execute(*, participation: LearnerPreparednessParticipation, learner_id):
        if participation.learner_id != learner_id:
            raise ValidationError("Only the owning learner can opt in.", code="LEARNER_PREPAREDNESS_ACCESS_DENIED")
        participation.ariel_opted_in_at = participation.ariel_opted_in_at or timezone.now()
        participation.version += 1
        participation.save(update_fields=["ariel_opted_in_at", "version"])
        return participation


class BuildClassPreparednessProjectionService:
    MIN_COHORT_SIZE = 5
    SUPPRESSION_THRESHOLD = 5

    @staticmethod
    def execute(*, assignment: ClassPreparednessAssignment):
        participations = list(assignment.participations.select_related("learner").all())
        participant_count = len(participations)
        if participant_count < BuildClassPreparednessProjectionService.MIN_COHORT_SIZE:
            return {
                "status": "INSUFFICIENT_COHORT_FOR_AGGREGATION",
                "participant_count": participant_count,
                "report_available": False,
                "population_mode": assignment.population_mode,
                "population_source": assignment.population_source,
            }

        responded = sum(1 for p in participations if p.status in {ParticipationStatus.RESPONDED, ParticipationStatus.COMPLETED})
        opted_in = sum(1 for p in participations if p.ariel_opted_in_at is not None)
        open_count = sum(1 for p in participations if p.status in {ParticipationStatus.OPEN, ParticipationStatus.STARTED})
        ariel_attempt_count = sum(1 for p in participations for a in p.ariel_attempts.all() if a.status == "completed")
        suppressed = participant_count < BuildClassPreparednessProjectionService.SUPPRESSION_THRESHOLD

        return {
            "status": "READY",
            "report_available": True,
            "population_mode": assignment.population_mode,
            "population_source": assignment.population_source,
            "participant_count": participant_count,
            "assigned_count": participant_count,
            "responded_count": None if suppressed else responded,
            "open_count": None if suppressed else open_count,
            "ariel_opt_in_count": None if suppressed else opted_in,
            "ariel_attempt_count": None if suppressed else ariel_attempt_count,
            "population_version": assignment.version,
            "reason_codes": [
                "DATA_SUFFICIENCY_ACCEPTABLE" if participant_count >= BuildClassPreparednessProjectionService.MIN_COHORT_SIZE else "DATA_SUFFICIENCY_INSUFFICIENT",
                "PRIVATE_PARTICIPATION_SUPPRESSED" if suppressed else "AGGREGATION_SAFE",
            ],
        }


class ResolvePreparednessAssignmentLearnersService:
    @staticmethod
    def execute(*, assignment: ClassPreparednessAssignment):
        return list(assignment.participations.values_list("learner_id", flat=True))


class CreatePreparednessPromptService:
    @staticmethod
    @transaction.atomic
    def execute(*, activity: PreparednessActivity, sequence: int, prompt_type: str, prompt_text: str, prerequisite_reference="", required=False, ariel_eligible=False):
        return PreparednessPrompt.objects.create(
            activity=activity,
            sequence=sequence,
            prompt_type=prompt_type,
            prompt_text=prompt_text,
            prerequisite_reference=prerequisite_reference,
            required=required,
            ariel_eligible=ariel_eligible,
        )
