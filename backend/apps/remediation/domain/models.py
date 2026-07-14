import uuid

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.academic.domain.models import ContentConcept, LearningResource
from apps.assessments.domain.models import LearningEvidence
from apps.core.exceptions import LifecycleTransitionError


class RemediationPlanStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    ESCALATED = "escalated", "Escalated"
    CANCELLED = "cancelled", "Cancelled"
    CLOSED = "closed", "Closed"


class RemediationRecommendationType(models.TextChoices):
    REVIEW_LESSON = "review_lesson", "Review Lesson"
    REPEAT_ACTIVITY = "repeat_activity", "Repeat Activity"
    TEACH_ARIEL = "teach_ariel", "Teach Ariel"
    ADDITIONAL_QUESTIONS = "additional_questions", "Additional Questions"
    READ_SOURCE_MATERIAL = "read_source_material", "Read Source Material"
    SIMULATION = "simulation", "Simulation"
    EDUCATOR_REVIEW = "educator_review", "Educator Review"
    PRACTICE_ASSESSMENT = "practice_assessment", "Practice Assessment"
    PROGRAMMING_TASK = "programming_task", "Programming Task"
    CUSTOM = "custom", "Custom"


class RemediationActivityType(models.TextChoices):
    LESSON_REPLAY = "lesson_replay", "Lesson Replay"
    PRACTICE_ASSESSMENT = "practice_assessment", "Practice Assessment"
    SIMULATION = "simulation", "Simulation"
    TEACH_ARIEL = "teach_ariel", "Teach Ariel"
    PROGRAMMING_TASK = "programming_task", "Programming Task"
    EDUCATOR_REVIEW = "educator_review", "Educator Review"
    CUSTOM = "custom", "Custom"


class RemediationActivityStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class RemediationAttemptStatus(models.TextChoices):
    STARTED = "started", "Started"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class RemediationOutcomeValue(models.TextChoices):
    IMPROVED = "improved", "Improved"
    UNCHANGED = "unchanged", "Unchanged"
    REGRESSED = "regressed", "Regressed"
    ESCALATED = "escalated", "Escalated"


@dataclass
class DomainRemediationPlan:
    learner: Any
    content_concept: Any
    trigger_evidence: Any | None = None
    status: str = RemediationPlanStatus.PENDING
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    id: Any | None = None
    learner_id: Any | None = None
    content_concept_id: Any | None = None

    def __post_init__(self) -> None:
        self.learner_id = self.learner_id or getattr(self.learner, "id", None)
        self.content_concept_id = self.content_concept_id or getattr(self.content_concept, "id", None)

    def activate(self) -> None:
        if self.status not in {RemediationPlanStatus.PENDING, RemediationPlanStatus.ACTIVE}:
            raise LifecycleTransitionError(f"Cannot start remediation plan from {self.status}.")
        self.status = RemediationPlanStatus.ACTIVE

    def complete(self) -> None:
        if self.status not in {RemediationPlanStatus.ACTIVE, RemediationPlanStatus.PENDING}:
            raise LifecycleTransitionError(f"Cannot complete remediation plan from {self.status}.")
        self.status = RemediationPlanStatus.COMPLETED

    def escalate(self) -> None:
        if self.status in {RemediationPlanStatus.CANCELLED, RemediationPlanStatus.CLOSED}:
            raise LifecycleTransitionError(f"Cannot escalate remediation plan from {self.status}.")
        self.status = RemediationPlanStatus.ESCALATED

    def cancel(self) -> None:
        if self.status in {RemediationPlanStatus.COMPLETED, RemediationPlanStatus.CLOSED}:
            raise LifecycleTransitionError(f"Cannot cancel remediation plan from {self.status}.")
        self.status = RemediationPlanStatus.CANCELLED

    def close(self) -> None:
        if self.status not in {RemediationPlanStatus.COMPLETED, RemediationPlanStatus.ESCALATED, RemediationPlanStatus.CANCELLED}:
            raise LifecycleTransitionError(f"Cannot close remediation plan from {self.status}.")
        self.status = RemediationPlanStatus.CLOSED


@dataclass
class DomainRemediationRecommendation:
    plan: Any
    recommendation_type: str
    title: str
    rationale: str = ""
    priority: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    id: Any | None = None

    def raise_priority(self) -> None:
        if self.priority > 1:
            self.priority -= 1


@dataclass
class DomainRemediationActivity:
    plan: Any
    recommendation: Any | None
    activity_type: str
    title: str
    instructions: str = ""
    status: str = RemediationActivityStatus.PLANNED
    evidence_producer_type: str = ""
    evidence_reference_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    id: Any | None = None

    def start(self) -> None:
        if self.status not in {RemediationActivityStatus.PLANNED, RemediationActivityStatus.ACTIVE}:
            raise LifecycleTransitionError(f"Cannot start remediation activity from {self.status}.")
        self.status = RemediationActivityStatus.ACTIVE

    def complete(self, evidence_reference_id: str = "") -> None:
        if self.status not in {RemediationActivityStatus.PLANNED, RemediationActivityStatus.ACTIVE}:
            raise LifecycleTransitionError(f"Cannot complete remediation activity from {self.status}.")
        self.status = RemediationActivityStatus.COMPLETED
        if evidence_reference_id:
            self.evidence_reference_id = evidence_reference_id


class RemediationPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="remediation_plans")
    content_concept = models.ForeignKey(ContentConcept, on_delete=models.CASCADE, related_name="remediation_plans")
    status = models.CharField(max_length=50, choices=RemediationPlanStatus.choices, default=RemediationPlanStatus.PENDING)
    trigger_evidence = models.ForeignKey(LearningEvidence, on_delete=models.SET_NULL, null=True, blank=True, related_name="triggered_remediation_plans")
    rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "remediation_plan"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["learner"], name="rem_plan_learner_idx"),
            models.Index(fields=["content_concept"], name="rem_plan_concept_idx"),
            models.Index(fields=["status"], name="rem_plan_status_idx"),
        ]

    def activate(self) -> None:
        if self.status not in {RemediationPlanStatus.PENDING, RemediationPlanStatus.ACTIVE}:
            raise LifecycleTransitionError(f"Cannot start remediation plan from {self.status}.")
        self.status = RemediationPlanStatus.ACTIVE
        self.started_at = self.started_at or timezone.now()

    def complete(self) -> None:
        if self.status not in {RemediationPlanStatus.ACTIVE, RemediationPlanStatus.PENDING}:
            raise LifecycleTransitionError(f"Cannot complete remediation plan from {self.status}.")
        self.status = RemediationPlanStatus.COMPLETED
        self.completed_at = timezone.now()

    def escalate(self) -> None:
        if self.status in {RemediationPlanStatus.CANCELLED, RemediationPlanStatus.CLOSED}:
            raise LifecycleTransitionError(f"Cannot escalate remediation plan from {self.status}.")
        self.status = RemediationPlanStatus.ESCALATED
        self.escalated_at = timezone.now()

    def cancel(self) -> None:
        if self.status in {RemediationPlanStatus.COMPLETED, RemediationPlanStatus.CLOSED}:
            raise LifecycleTransitionError(f"Cannot cancel remediation plan from {self.status}.")
        self.status = RemediationPlanStatus.CANCELLED
        self.cancelled_at = timezone.now()

    def close(self) -> None:
        if self.status not in {RemediationPlanStatus.COMPLETED, RemediationPlanStatus.ESCALATED, RemediationPlanStatus.CANCELLED}:
            raise LifecycleTransitionError(f"Cannot close remediation plan from {self.status}.")
        self.status = RemediationPlanStatus.CLOSED
        self.closed_at = timezone.now()


class RemediationRecommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(RemediationPlan, on_delete=models.CASCADE, related_name="recommendations")
    recommendation_type = models.CharField(max_length=100, choices=RemediationRecommendationType.choices)
    title = models.CharField(max_length=255)
    rationale = models.TextField(blank=True)
    priority = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "remediation_recommendation"
        ordering = ["priority", "created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(priority__gte=1), name="rem_recommendation_priority_gte_1"),
        ]

    def raise_priority(self) -> None:
        if self.priority > 1:
            self.priority -= 1


class RemediationActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(RemediationPlan, on_delete=models.CASCADE, related_name="activities")
    recommendation = models.ForeignKey(RemediationRecommendation, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    activity_type = models.CharField(max_length=100, choices=RemediationActivityType.choices)
    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=RemediationActivityStatus.choices, default=RemediationActivityStatus.PLANNED)
    evidence_producer_type = models.CharField(max_length=100, blank=True)
    evidence_reference_id = models.CharField(max_length=255, blank=True)
    resource = models.ForeignKey(LearningResource, on_delete=models.SET_NULL, null=True, blank=True, related_name="remediation_activities")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "remediation_activity"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["activity_type"], name="rem_activity_type_idx"),
            models.Index(fields=["status"], name="rem_activity_status_idx"),
        ]

    def start(self) -> None:
        if self.status not in {RemediationActivityStatus.PLANNED, RemediationActivityStatus.ACTIVE}:
            raise LifecycleTransitionError(f"Cannot start remediation activity from {self.status}.")
        self.status = RemediationActivityStatus.ACTIVE

    def complete(self, evidence_reference_id: str = "") -> None:
        if self.status not in {RemediationActivityStatus.PLANNED, RemediationActivityStatus.ACTIVE}:
            raise LifecycleTransitionError(f"Cannot complete remediation activity from {self.status}.")
        self.status = RemediationActivityStatus.COMPLETED
        if evidence_reference_id:
            self.evidence_reference_id = evidence_reference_id


class RemediationAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(RemediationActivity, on_delete=models.CASCADE, related_name="attempts")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="remediation_attempts")
    status = models.CharField(max_length=50, choices=RemediationAttemptStatus.choices, default=RemediationAttemptStatus.STARTED)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "remediation_attempt"
        ordering = ["-created_at"]

    def complete(self) -> None:
        self.status = RemediationAttemptStatus.COMPLETED
        self.completed_at = timezone.now()


class RemediationOutcome(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(RemediationPlan, on_delete=models.CASCADE, related_name="outcomes")
    activity = models.ForeignKey(RemediationActivity, on_delete=models.SET_NULL, null=True, blank=True, related_name="outcomes")
    outcome = models.CharField(max_length=50, choices=RemediationOutcomeValue.choices)
    supporting_evidence = models.ForeignKey(LearningEvidence, on_delete=models.SET_NULL, null=True, blank=True, related_name="remediation_outcomes")
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "remediation_outcome"
        ordering = ["-recorded_at"]

    def requires_escalation(self) -> bool:
        return self.outcome == RemediationOutcomeValue.ESCALATED


__all__ = [
    "RemediationPlan",
    "DomainRemediationPlan",
    "RemediationRecommendation",
    "DomainRemediationRecommendation",
    "RemediationActivity",
    "DomainRemediationActivity",
    "RemediationAttempt",
    "RemediationOutcome",
    "RemediationPlanStatus",
    "RemediationRecommendationType",
    "RemediationActivityType",
    "RemediationActivityStatus",
    "RemediationAttemptStatus",
    "RemediationOutcomeValue",
]
