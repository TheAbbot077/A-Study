from __future__ import annotations

import uuid
from django.db import models


class TeachingReadinessEvaluation(models.Model):
    class Decision(models.TextChoices):
        READY = "ready", "Ready"
        BLOCKED = "blocked", "Blocked"
        STALE = "stale", "Stale"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, related_name="teaching_readiness_evaluations")
    subject = models.ForeignKey("academic.Subject", on_delete=models.PROTECT, related_name="teaching_readiness_evaluations")
    processing_job = models.ForeignKey("content_processing.ContentProcessingJob", on_delete=models.PROTECT, related_name="teaching_readiness_evaluations")
    processing_attempt_id = models.UUIDField(null=True, blank=True)
    approved_projection_id = models.UUIDField(null=True, blank=True)
    approval_decision_id = models.UUIDField(null=True, blank=True)
    academic_population_run_id = models.UUIDField(null=True, blank=True)
    retrieval_synchronization_run_id = models.UUIDField(null=True, blank=True)
    retrieval_generation_id = models.UUIDField(null=True, blank=True)
    requested_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="teaching_readiness_evaluations")
    trigger = models.CharField(max_length=32, default="staff")
    reason = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=128, unique=True)
    request_fingerprint = models.CharField(max_length=128)
    lineage_fingerprint = models.CharField(max_length=128)
    policy_version = models.CharField(max_length=64)
    decision = models.CharField(max_length=16, choices=Decision.choices)
    checks_passed = models.PositiveIntegerField(default=0)
    checks_failed = models.PositiveIntegerField(default=0)
    blocker_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    snapshot = models.JSONField(default=dict)
    checks = models.JSONField(default=list)
    supersedes_evaluation = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="superseded_by")
    invalidated_at = models.DateTimeField(null=True, blank=True)
    invalidation_reason = models.CharField(max_length=128, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_teaching_readiness_evaluation"
        ordering = ["-evaluated_at"]
        constraints = [
            models.UniqueConstraint(fields=["resource", "lineage_fingerprint", "policy_version"], name="cp_readiness_lineage_policy_unique"),
        ]
        indexes = [
            models.Index(fields=["resource", "decision"], name="cp_ready_resource_decision"),
            models.Index(fields=["processing_job", "evaluated_at"], name="cp_ready_job_evaluated"),
            models.Index(fields=["lineage_fingerprint"], name="cp_ready_lineage"),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            update_fields = set(kwargs.get("update_fields") or ())
            if not update_fields or not update_fields <= {"invalidated_at", "invalidation_reason"}:
                raise ValueError("Teaching-readiness evaluations are immutable.")
        super().save(*args, **kwargs)
