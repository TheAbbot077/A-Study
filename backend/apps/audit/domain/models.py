import uuid
from typing import Any

from django.db import models

from apps.users.domain.models import Institution, User


class AuditEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_entries")
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_entries")
    action = models.CharField(max_length=255)
    target_type = models.CharField(max_length=255, blank=True)
    target_id = models.CharField(max_length=255, blank=True)
    target_display = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_audit_entry"
        indexes = [
            models.Index(fields=["actor"], name="audit_actor_idx"),
            models.Index(fields=["institution"], name="audit_inst_idx"),
            models.Index(fields=["action"], name="audit_action_idx"),
            models.Index(fields=["target_type", "target_id"], name="audit_target_idx"),
            models.Index(fields=["created_at"], name="audit_created_idx"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"AuditEntry {self.action}"
