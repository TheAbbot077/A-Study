from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .enums import (
    LearningCompetencyProgressReason,
    LearningCompetencyProgressState,
    LearningCompetencyUnlockState,
    LearningJourneySourceType,
    LearningJourneyStatus,
    LearningJourneyStatusReasonCode,
    LearningJourneyActionReceiptStatus,
    LearningJourneySubjectBindingSource,
    LearningJourneySubjectBindingStatus,
    LearningJourneyType,
)
from .policies import LearningJourneyLifecyclePolicy


class LearningJourney(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="learning_journeys")
    journey_type = models.CharField(max_length=32, choices=LearningJourneyType.choices)
    institution = models.ForeignKey(
        "users.Institution",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="learning_journeys",
    )
    status = models.CharField(max_length=40, choices=LearningJourneyStatus.choices, default=LearningJourneyStatus.CREATED)
    status_reason_code = models.CharField(
        max_length=64,
        choices=LearningJourneyStatusReasonCode.choices,
        default=LearningJourneyStatusReasonCode.JOURNEY_CREATED,
    )
    status_reason_message = models.CharField(max_length=500, blank=True)
    current_step_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    last_synchronized_at = models.DateTimeField(null=True, blank=True)
    projection_version = models.PositiveIntegerField(default=1)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "learning_journey"
        indexes = [
            models.Index(fields=["learner", "status"], name="lj_learner_status_idx"),
            models.Index(fields=["institution", "status"], name="lj_institution_status_idx"),
            models.Index(fields=["journey_type", "status"], name="lj_type_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(journey_type=LearningJourneyType.INSTITUTIONAL, institution__isnull=False)
                | Q(journey_type=LearningJourneyType.SELF_STUDY),
                name="lj_institutional_requires_institution",
            ),
        ]

    def clean(self):
        super().clean()
        if self.journey_type == LearningJourneyType.INSTITUTIONAL and not self.institution_id:
            raise ValidationError("Institutional journeys require institution authority.", code="INSTITUTION_REQUIRED")

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            if old:
                if old.learner_id != self.learner_id:
                    raise ValidationError("Journey learner is immutable.", code="LEARNING_JOURNEY_LEARNER_IMMUTABLE")
                if old.journey_type != self.journey_type:
                    raise ValidationError("Journey type is immutable.", code="LEARNING_JOURNEY_TYPE_IMMUTABLE")
                if old.institution_id != self.institution_id:
                    raise ValidationError("Journey institution authority is immutable.", code="LEARNING_JOURNEY_INSTITUTION_IMMUTABLE")
        self.full_clean()
        return super().save(*args, **kwargs)

    def transition_to(
        self,
        status: str,
        *,
        reason_code: str,
        reason_message: str = "",
        current_step_code: str = "",
        when=None,
    ) -> bool:
        if self.status == status and self.status_reason_code == reason_code and self.current_step_code == current_step_code:
            return False
        LearningJourneyLifecyclePolicy.validate(self.status, status)
        when = when or timezone.now()
        previous = self.status
        self.status = status
        self.status_reason_code = reason_code
        self.status_reason_message = reason_message
        self.current_step_code = current_step_code
        if previous == LearningJourneyStatus.CREATED and status != LearningJourneyStatus.CREATED and not self.started_at:
            self.started_at = when
        if status == LearningJourneyStatus.PAUSED:
            self.paused_at = when
        if status == LearningJourneyStatus.LEARNING_GOAL_COMPLETED:
            self.completed_at = when
        if status == LearningJourneyStatus.WITHDRAWN:
            self.withdrawn_at = when
        if status == LearningJourneyStatus.ARCHIVED:
            self.archived_at = when
        self.version += 1
        self.projection_version += 1
        return True


class LearningJourneySourceBinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journey = models.ForeignKey(LearningJourney, on_delete=models.PROTECT, related_name="source_bindings")
    source_type = models.CharField(max_length=40, choices=LearningJourneySourceType.choices)
    source_id = models.UUIDField()
    source_version = models.PositiveIntegerField(null=True, blank=True)
    bound_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "learning_journey_source_binding"
        constraints = [
            models.UniqueConstraint(fields=["source_type", "source_id"], name="lj_source_unique"),
            models.UniqueConstraint(fields=["journey", "source_type"], name="lj_source_type_per_journey_unique"),
        ]
        indexes = [models.Index(fields=["source_type", "source_id"], name="lj_source_lookup_idx")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Journey source bindings are immutable.", code="LEARNING_JOURNEY_SOURCE_IMMUTABLE")
        return super().save(*args, **kwargs)


class LearningJourneySubjectBinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journey = models.ForeignKey(LearningJourney, on_delete=models.PROTECT, related_name="subject_bindings")
    subject = models.ForeignKey("academic.Subject", on_delete=models.PROTECT, related_name="learning_journey_bindings")
    curriculum_reference = models.ForeignKey(
        "self_study.CurriculumReference",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="learning_journey_subject_bindings",
    )
    binding_source = models.CharField(max_length=48, choices=LearningJourneySubjectBindingSource.choices)
    binding_authority_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=LearningJourneySubjectBindingStatus.choices,
        default=LearningJourneySubjectBindingStatus.ACTIVE,
    )
    bound_at = models.DateTimeField(auto_now_add=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "learning_journey_subject_binding"
        constraints = [
            models.UniqueConstraint(
                fields=["journey"],
                condition=Q(status=LearningJourneySubjectBindingStatus.ACTIVE),
                name="lj_one_active_subject_binding",
            ),
        ]
        indexes = [models.Index(fields=["journey", "status"], name="lj_subj_binding_status_idx")]

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            if old:
                frozen = ("journey_id", "subject_id", "curriculum_reference_id", "binding_source", "binding_authority_id", "bound_at")
                if any(getattr(old, field) != getattr(self, field) for field in frozen):
                    raise ValidationError("Journey subject binding authority is immutable.", code="LEARNING_JOURNEY_SUBJECT_BINDING_IMMUTABLE")
        return super().save(*args, **kwargs)

    def supersede(self, *, when=None) -> bool:
        if self.status == LearningJourneySubjectBindingStatus.SUPERSEDED:
            return False
        self.status = LearningJourneySubjectBindingStatus.SUPERSEDED
        self.superseded_at = when or timezone.now()
        self.version += 1
        return True


class LearningJourneyCapabilityReferences(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journey = models.OneToOneField(LearningJourney, on_delete=models.PROTECT, related_name="capability_references")
    intent_id = models.UUIDField(null=True, blank=True)
    curriculum_resolution_attempt_id = models.UUIDField(null=True, blank=True)
    diagnostic_id = models.UUIDField(null=True, blank=True)
    placement_id = models.UUIDField(null=True, blank=True)
    bridge_plan_id = models.UUIDField(null=True, blank=True)
    learning_plan_id = models.UUIDField(null=True, blank=True)
    teaching_preparation_id = models.UUIDField(null=True, blank=True)
    active_teaching_session_id = models.UUIDField(null=True, blank=True)
    remediation_plan_id = models.UUIDField(null=True, blank=True)
    references_snapshot = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "learning_journey_capability_references"

    def update_from_projection(self, references: dict) -> bool:
        changed = False
        field_map = {
            "intent_id": "intent_id",
            "curriculum_resolution_attempt_id": "curriculum_resolution_attempt_id",
            "diagnostic_id": "diagnostic_id",
            "placement_id": "placement_id",
            "bridge_plan_id": "bridge_plan_id",
            "learning_plan_id": "learning_plan_id",
            "teaching_preparation_id": "teaching_preparation_id",
            "active_teaching_session_id": "active_teaching_session_id",
            "remediation_plan_id": "remediation_plan_id",
        }
        for key, field in field_map.items():
            value = references.get(key) or None
            if str(getattr(self, field) or "") != str(value or ""):
                setattr(self, field, value)
                changed = True
        snapshot = dict(references)
        if self.references_snapshot != snapshot:
            self.references_snapshot = snapshot
            changed = True
        if changed:
            self.version += 1
        return changed


class LearningJourneyActionReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journey = models.ForeignKey(LearningJourney, on_delete=models.PROTECT, related_name="action_receipts")
    action_code = models.CharField(max_length=64)
    actor = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="learning_journey_action_receipts")
    idempotency_key = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=16,
        choices=LearningJourneyActionReceiptStatus.choices,
        default=LearningJourneyActionReceiptStatus.ACCEPTED,
    )
    source_capability = models.CharField(max_length=96, blank=True)
    source_record_id = models.UUIDField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=96, blank=True)
    failure_message = models.CharField(max_length=500, blank=True)
    request_metadata = models.JSONField(default=dict, blank=True)
    result_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "learning_journey_action_receipt"
        indexes = [
            models.Index(fields=["journey", "action_code", "status"], name="lj_receipt_action_status_idx"),
            models.Index(fields=["actor", "started_at"], name="lj_receipt_actor_time_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["journey", "action_code", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="lj_action_receipt_idempotency_unique",
            ),
        ]

    def mark_succeeded(self, *, source_capability: str = "", source_record_id=None, result_metadata: dict | None = None):
        self.status = LearningJourneyActionReceiptStatus.SUCCEEDED
        self.source_capability = source_capability
        self.source_record_id = source_record_id
        self.result_metadata = result_metadata or {}
        self.completed_at = timezone.now()

    def mark_rejected(self, *, code: str, message: str, result_metadata: dict | None = None):
        self.status = LearningJourneyActionReceiptStatus.REJECTED
        self.failure_code = code
        self.failure_message = message[:500]
        self.result_metadata = result_metadata or {}
        self.completed_at = timezone.now()

    def mark_failed(self, *, code: str, message: str, result_metadata: dict | None = None):
        self.status = LearningJourneyActionReceiptStatus.FAILED
        self.failure_code = code
        self.failure_message = message[:500]
        self.result_metadata = result_metadata or {}
        self.completed_at = timezone.now()

    def mark_no_op(self, *, result_metadata: dict | None = None):
        self.status = LearningJourneyActionReceiptStatus.NO_OP
        self.result_metadata = result_metadata or {}
        self.completed_at = timezone.now()


class LearningCompetencyProgress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journey = models.ForeignKey(LearningJourney, on_delete=models.PROTECT, related_name="competency_progress")
    competency = models.ForeignKey("self_study.CurriculumNode", on_delete=models.PROTECT, related_name="learning_journey_progress")
    state = models.CharField(
        max_length=24,
        choices=LearningCompetencyProgressState.choices,
        default=LearningCompetencyProgressState.NOT_STARTED,
    )
    unlock_state = models.CharField(
        max_length=16,
        choices=LearningCompetencyUnlockState.choices,
        default=LearningCompetencyUnlockState.LOCKED,
    )
    latest_mastery_decision = models.ForeignKey(
        "assessments.MasteryDecision",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="learning_competency_progress",
    )
    latest_evidence_summary = models.JSONField(default=dict, blank=True)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    first_demonstrated_at = models.DateTimeField(null=True, blank=True)
    last_progressed_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    superseded_by = models.ForeignKey(
        "self_study.CurriculumNode",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="superseded_learning_progress",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "learning_competency_progress"
        constraints = [
            models.UniqueConstraint(fields=["journey", "competency"], name="lj_competency_progress_unique"),
        ]
        indexes = [
            models.Index(fields=["journey", "state"], name="lj_comp_progress_state_idx"),
            models.Index(fields=["journey", "unlock_state"], name="lj_comp_unlock_state_idx"),
            models.Index(fields=["competency", "state"], name="lj_competency_state_idx"),
        ]

    def transition_to(
        self,
        state: str,
        *,
        unlock_state: str | None = None,
        mastery_decision=None,
        evidence_summary: dict | None = None,
        when=None,
    ) -> bool:
        when = when or timezone.now()
        changed = False
        if self.state != state:
            self.state = state
            changed = True
            if state == LearningCompetencyProgressState.DEMONSTRATED and not self.first_demonstrated_at:
                self.first_demonstrated_at = when
            if state == LearningCompetencyProgressState.SUPERSEDED:
                self.superseded_at = when
        if unlock_state and self.unlock_state != unlock_state:
            self.unlock_state = unlock_state
            changed = True
            if unlock_state in {LearningCompetencyUnlockState.AVAILABLE, LearningCompetencyUnlockState.ACTIVE} and not self.unlocked_at:
                self.unlocked_at = when
        if mastery_decision and self.latest_mastery_decision_id != mastery_decision.id:
            self.latest_mastery_decision = mastery_decision
            changed = True
        if evidence_summary is not None and self.latest_evidence_summary != evidence_summary:
            self.latest_evidence_summary = evidence_summary
            changed = True
        if changed:
            self.last_progressed_at = when
            self.version += 1
        return changed


class LearningCompetencyProgressHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    progress = models.ForeignKey(LearningCompetencyProgress, on_delete=models.PROTECT, related_name="history")
    journey = models.ForeignKey(LearningJourney, on_delete=models.PROTECT, related_name="competency_progress_history")
    competency = models.ForeignKey("self_study.CurriculumNode", on_delete=models.PROTECT, related_name="learning_progress_history")
    old_state = models.CharField(max_length=24, choices=LearningCompetencyProgressState.choices)
    new_state = models.CharField(max_length=24, choices=LearningCompetencyProgressState.choices)
    old_unlock_state = models.CharField(max_length=16, choices=LearningCompetencyUnlockState.choices)
    new_unlock_state = models.CharField(max_length=16, choices=LearningCompetencyUnlockState.choices)
    reason = models.CharField(
        max_length=48,
        choices=LearningCompetencyProgressReason.choices,
        default=LearningCompetencyProgressReason.UNCHANGED,
    )
    triggering_evidence_id = models.UUIDField(null=True, blank=True)
    triggering_mastery_decision = models.ForeignKey(
        "assessments.MasteryDecision",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="learning_competency_progress_history",
    )
    actor = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="learning_competency_progress_events",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "learning_competency_progress_history"
        indexes = [
            models.Index(fields=["journey", "created_at"], name="lj_comp_hist_journey_time_idx"),
            models.Index(fields=["competency", "new_state"], name="lj_comp_hist_state_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Competency progress history is append-only.", code="COMPETENCY_HISTORY_APPEND_ONLY")
        return super().save(*args, **kwargs)
