import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.educational_organization.domain.models import ClassGroup, CourseOffering, TeachingAssignment
from apps.users.domain.models import Institution

from .enums import (
    ArielPreparednessAttemptStatus,
    PreparednessAssignmentPopulationMode,
    LessonPreparationStatus,
    ParticipationStatus,
    PreparednessActivityStatus,
    PreparednessPromptType,
    PrerequisitePriority,
)
from .policies import LessonPreparationLifecyclePolicy, ParticipationLifecyclePolicy, PreparednessActivityLifecyclePolicy


class LessonPreparation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="lesson_preparations")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="lesson_preparations")
    teaching_assignment = models.ForeignKey(TeachingAssignment, on_delete=models.PROTECT, related_name="lesson_preparations")
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT, related_name="lesson_preparations")
    class_group = models.ForeignKey(ClassGroup, on_delete=models.PROTECT, related_name="lesson_preparations")
    title = models.CharField(max_length=255)
    topic_reference = models.CharField(max_length=255, blank=True)
    lesson_date = models.DateField(null=True, blank=True)
    learning_objective = models.TextField()
    status = models.CharField(max_length=24, choices=LessonPreparationStatus.choices, default=LessonPreparationStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "classroom_lesson_preparation"

    def transition_to(self, status: str, *, when=None) -> bool:
        if self.status == status:
            return False
        LessonPreparationLifecyclePolicy.validate(self.status, status)
        when = when or timezone.now()
        self.status = status
        if status == LessonPreparationStatus.PUBLISHED:
            self.published_at = when
        elif status == LessonPreparationStatus.COMPLETED:
            self.completed_at = when
        elif status == LessonPreparationStatus.CANCELLED:
            self.cancelled_at = when
        elif status == LessonPreparationStatus.ARCHIVED:
            self.archived_at = when
        self.version += 1
        return True


class LessonPrerequisite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson_preparation = models.ForeignKey(LessonPreparation, on_delete=models.PROTECT, related_name="prerequisites")
    authority_type = models.CharField(max_length=64)
    authority_reference = models.CharField(max_length=255)
    priority = models.CharField(max_length=16, choices=PrerequisitePriority.choices, default=PrerequisitePriority.IMPORTANT)
    sequence = models.PositiveIntegerField(default=1)
    teacher_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "classroom_lesson_prerequisite"
        constraints = [models.UniqueConstraint(fields=["lesson_preparation", "sequence"], name="classroom_lesson_prereq_sequence_unique")]


class PreparednessActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson_preparation = models.ForeignKey(LessonPreparation, on_delete=models.PROTECT, related_name="activities")
    title = models.CharField(max_length=255)
    purpose = models.CharField(max_length=64, default="LESSON_PREPARATION")
    status = models.CharField(max_length=24, choices=PreparednessActivityStatus.choices, default=PreparednessActivityStatus.DRAFT)
    instructions = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="preparedness_activities")
    available_from = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "classroom_preparedness_activity"

    def transition_to(self, status: str, *, when=None) -> bool:
        if self.status == status:
            return False
        PreparednessActivityLifecyclePolicy.validate(self.status, status)
        self.status = status
        self.version += 1
        return True


class PreparednessPrompt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(PreparednessActivity, on_delete=models.PROTECT, related_name="prompts")
    sequence = models.PositiveIntegerField(default=1)
    prompt_type = models.CharField(max_length=32, choices=PreparednessPromptType.choices)
    prompt_text = models.TextField()
    prerequisite_reference = models.CharField(max_length=255, blank=True)
    required = models.BooleanField(default=False)
    ariel_eligible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "classroom_preparedness_prompt"
        constraints = [models.UniqueConstraint(fields=["activity", "sequence"], name="classroom_preparedness_prompt_sequence_unique")]


class ClassPreparednessAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(PreparednessActivity, on_delete=models.PROTECT, related_name="assignments")
    class_group = models.ForeignKey(ClassGroup, on_delete=models.PROTECT, related_name="preparedness_assignments")
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT, related_name="preparedness_assignments")
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="preparedness_assignments")
    population_mode = models.CharField(
        max_length=32,
        choices=PreparednessAssignmentPopulationMode.choices,
        default=PreparednessAssignmentPopulationMode.EXPLICIT_PARTICIPANTS,
    )
    population_source = models.CharField(max_length=128, default="PREPAREDNESS_PARTICIPATION_RECORDS")
    status = models.CharField(max_length=24, choices=PreparednessActivityStatus.choices, default=PreparednessActivityStatus.PUBLISHED)
    available_from = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "classroom_preparedness_assignment"
        constraints = [models.UniqueConstraint(fields=["activity", "class_group"], name="classroom_assignment_unique")]


class LearnerPreparednessParticipation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(ClassPreparednessAssignment, on_delete=models.PROTECT, related_name="participations")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="preparedness_participations")
    status = models.CharField(max_length=24, choices=ParticipationStatus.choices, default=ParticipationStatus.ASSIGNED)
    started_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    ariel_opted_in_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "classroom_learner_preparedness_participation"
        constraints = [models.UniqueConstraint(fields=["assignment", "learner"], name="classroom_participation_unique")]

    def transition_to(self, status: str, *, when=None) -> bool:
        if self.status == status:
            return False
        ParticipationLifecyclePolicy.validate(self.status, status)
        when = when or timezone.now()
        self.status = status
        if status == ParticipationStatus.STARTED:
            self.started_at = when
        elif status == ParticipationStatus.RESPONDED:
            self.responded_at = when
        elif status == ParticipationStatus.COMPLETED:
            self.completed_at = when
        self.version += 1
        return True


class ArielPreparednessAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participation = models.ForeignKey(LearnerPreparednessParticipation, on_delete=models.PROTECT, related_name="ariel_attempts")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ariel_preparedness_attempts")
    ariel_identity_id = models.UUIDField()
    prompt = models.ForeignKey(PreparednessPrompt, on_delete=models.PROTECT, related_name="ariel_attempts")
    status = models.CharField(max_length=32, choices=ArielPreparednessAttemptStatus.choices, default=ArielPreparednessAttemptStatus.CREATED)
    constitution_version = models.CharField(max_length=32, blank=True)
    policy_version = models.CharField(max_length=32, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    signal_classifications = models.JSONField(default=list, blank=True)
    safe_summary_metadata = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "classroom_ariel_preparedness_attempt"
        constraints = [models.UniqueConstraint(fields=["participation", "prompt"], name="classroom_ariel_attempt_unique")]
