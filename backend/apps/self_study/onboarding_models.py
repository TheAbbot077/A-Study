from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class SelfStudyOnboardingStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    COLLECTING_CONTEXT = "COLLECTING_CONTEXT", "Collecting context"
    RESOLVING_CURRICULUM = "RESOLVING_CURRICULUM", "Resolving curriculum"
    AWAITING_CURRICULUM_SELECTION = "AWAITING_CURRICULUM_SELECTION", "Awaiting curriculum selection"
    REVIEWING_SUMMARY = "REVIEWING_SUMMARY", "Reviewing summary"
    COMPLETED = "COMPLETED", "Completed"
    STALE = "STALE", "Stale"
    ABANDONED = "ABANDONED", "Abandoned"


class SelfStudyOnboardingStage(models.TextChoices):
    STUDY_TOPIC = "STUDY_TOPIC", "Study topic"
    STUDY_INTENT = "STUDY_INTENT", "Study intent"
    QUALIFICATION_CONTEXT = "QUALIFICATION_CONTEXT", "Qualification context"
    CURRICULUM_DISCOVERY = "CURRICULUM_DISCOVERY", "Curriculum discovery"
    CURRICULUM_SELECTION = "CURRICULUM_SELECTION", "Curriculum selection"
    TARGET_DATE = "TARGET_DATE", "Target date"
    WEEKLY_AVAILABILITY = "WEEKLY_AVAILABILITY", "Weekly availability"
    SUMMARY = "SUMMARY", "Summary"
    COMPLETED = "COMPLETED", "Completed"


class SelfStudyOnboardingIntent(models.TextChoices):
    EXAM = "EXAM", "Study for an exam"
    LEARN_NEW = "LEARN_NEW", "Learn something new"
    MASTER_SUBJECT = "MASTER_SUBJECT", "Learn and master a subject"


class SelfStudyOnboarding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="self_study_onboardings")
    learner = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="self_study_onboardings")
    workspace = models.ForeignKey("self_study.SelfStudyWorkspace", on_delete=models.PROTECT, related_name="onboarding_sessions")
    status = models.CharField(max_length=40, choices=SelfStudyOnboardingStatus.choices, default=SelfStudyOnboardingStatus.COLLECTING_CONTEXT)
    current_stage = models.CharField(max_length=40, choices=SelfStudyOnboardingStage.choices, default=SelfStudyOnboardingStage.STUDY_TOPIC)
    topic_query = models.CharField(max_length=255, blank=True)
    study_intent = models.CharField(max_length=32, choices=SelfStudyOnboardingIntent.choices, blank=True)
    qualification_query = models.CharField(max_length=255, blank=True)
    jurisdiction_query = models.CharField(max_length=64, blank=True)
    awarding_body_query = models.CharField(max_length=128, blank=True)
    level_query = models.CharField(max_length=64, blank=True)
    target_description = models.CharField(max_length=255, blank=True)
    target_date = models.DateField(null=True, blank=True)
    target_date_known = models.BooleanField(default=False)
    weekly_study_minutes = models.PositiveIntegerField(null=True, blank=True)
    active_resolution_attempt = models.ForeignKey(
        "self_study.CurriculumResolutionAttempt",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="onboarding_sessions",
    )
    selected_curriculum_version = models.ForeignKey(
        "self_study.CurriculumVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="selected_for_onboardings",
    )
    selected_resolution_candidate = models.ForeignKey(
        "self_study.CurriculumResolutionCandidate",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="selected_for_onboardings",
    )
    selected_candidate_snapshot = models.JSONField(default=dict, blank=True)
    created_intent = models.ForeignKey(
        "self_study.SelfStudyIntent",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="onboarding_sessions",
    )
    idempotency_key = models.CharField(max_length=128, blank=True)
    stale_reason = models.CharField(max_length=128, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    abandoned_at = models.DateTimeField(null=True, blank=True)
    stale_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "self_study_onboarding"
        indexes = [
            models.Index(fields=["learner", "status"], name="ssi_onboard_learner_idx"),
            models.Index(fields=["workspace", "status"], name="ssi_onboard_workspace_idx"),
            models.Index(fields=["tenant", "status"], name="ssi_onboard_tenant_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="ssi_onboard_idem_unique",
            ),
        ]

    def require_editable(self):
        if self.status in {
            SelfStudyOnboardingStatus.COMPLETED,
            SelfStudyOnboardingStatus.ABANDONED,
            SelfStudyOnboardingStatus.STALE,
        }:
            raise ValidationError("Onboarding is not editable.", code="ONBOARDING_NOT_EDITABLE")

    def abandon(self, *, when):
        if self.status == SelfStudyOnboardingStatus.ABANDONED:
            return False
        if self.status == SelfStudyOnboardingStatus.COMPLETED:
            raise ValidationError("Completed onboarding cannot be abandoned.", code="ONBOARDING_NOT_EDITABLE")
        self.status = SelfStudyOnboardingStatus.ABANDONED
        self.abandoned_at = when
        self.version += 1
        return True
