from django.core.exceptions import ValidationError

from .enums import LessonPreparationStatus, PreparednessActivityStatus, ParticipationStatus


class LessonPreparationLifecyclePolicy:
    ALLOWED = {
        LessonPreparationStatus.DRAFT: {LessonPreparationStatus.READY, LessonPreparationStatus.CANCELLED},
        LessonPreparationStatus.READY: {LessonPreparationStatus.DRAFT, LessonPreparationStatus.PUBLISHED, LessonPreparationStatus.CANCELLED},
        LessonPreparationStatus.PUBLISHED: {LessonPreparationStatus.COMPLETED, LessonPreparationStatus.CANCELLED},
        LessonPreparationStatus.COMPLETED: {LessonPreparationStatus.ARCHIVED},
        LessonPreparationStatus.CANCELLED: {LessonPreparationStatus.ARCHIVED},
        LessonPreparationStatus.ARCHIVED: set(),
    }

    @staticmethod
    def validate(current, target):
        if target not in LessonPreparationLifecyclePolicy.ALLOWED.get(current, set()):
            raise ValidationError("Invalid lesson preparation transition.", code="LESSON_PREPARATION_INVALID_TRANSITION")


class PreparednessActivityLifecyclePolicy:
    ALLOWED = {
        PreparednessActivityStatus.DRAFT: {PreparednessActivityStatus.PUBLISHED, PreparednessActivityStatus.CANCELLED},
        PreparednessActivityStatus.PUBLISHED: {PreparednessActivityStatus.OPEN, PreparednessActivityStatus.CLOSED, PreparednessActivityStatus.CANCELLED},
        PreparednessActivityStatus.OPEN: {PreparednessActivityStatus.CLOSED, PreparednessActivityStatus.CANCELLED},
        PreparednessActivityStatus.CLOSED: {PreparednessActivityStatus.ARCHIVED},
        PreparednessActivityStatus.CANCELLED: {PreparednessActivityStatus.ARCHIVED},
        PreparednessActivityStatus.ARCHIVED: set(),
    }

    @staticmethod
    def validate(current, target):
        if target not in PreparednessActivityLifecyclePolicy.ALLOWED.get(current, set()):
            raise ValidationError("Invalid preparedness activity transition.", code="PREPAREDNESS_ACTIVITY_INVALID_TRANSITION")


class ParticipationLifecyclePolicy:
    ALLOWED = {
        ParticipationStatus.ASSIGNED: {ParticipationStatus.OPEN, ParticipationStatus.DECLINED, ParticipationStatus.EXPIRED},
        ParticipationStatus.OPEN: {ParticipationStatus.STARTED, ParticipationStatus.DECLINED, ParticipationStatus.EXPIRED, ParticipationStatus.COMPLETED},
        ParticipationStatus.STARTED: {ParticipationStatus.RESPONDED, ParticipationStatus.COMPLETED, ParticipationStatus.DECLINED, ParticipationStatus.EXPIRED},
        ParticipationStatus.RESPONDED: {ParticipationStatus.COMPLETED, ParticipationStatus.EXPIRED},
        ParticipationStatus.COMPLETED: set(),
        ParticipationStatus.DECLINED: set(),
        ParticipationStatus.EXPIRED: set(),
    }

    @staticmethod
    def validate(current, target):
        if target not in ParticipationLifecyclePolicy.ALLOWED.get(current, set()):
            raise ValidationError("Invalid participation transition.", code="LEARNER_PREPAREDNESS_INVALID_TRANSITION")
