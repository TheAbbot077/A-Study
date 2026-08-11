import uuid

from django.conf import settings
from django.db import models


class StoredFileSecurityScope(models.TextChoices):
    PRIVATE_LEARNER = "private_learner", "Private learner"
    INSTITUTION_SHARED = "institution_shared", "Institution shared"
    SYSTEM_MANAGED = "system_managed", "System managed"
    LEGACY_RESTRICTED = "legacy_restricted", "Legacy restricted"


class StoredFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_filename = models.CharField(max_length=512)
    stored_filename = models.CharField(max_length=512)
    content_type = models.CharField(max_length=128, blank=True, null=True)
    size_bytes = models.BigIntegerField()
    checksum = models.CharField(max_length=128, blank=True, null=True)
    provider = models.CharField(max_length=128)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stored_files",
        null=True,
        blank=True,
    )
    tenant = models.ForeignKey(
        "users.Institution",
        on_delete=models.PROTECT,
        related_name="stored_files",
        null=True,
        blank=True,
    )
    security_scope = models.CharField(
        max_length=32,
        choices=StoredFileSecurityScope.choices,
        default=StoredFileSecurityScope.PRIVATE_LEARNER,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "storage_storedfile"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "security_scope"], name="storedfile_owner_scope_idx"),
            models.Index(fields=["tenant", "security_scope"], name="storedfile_tenant_scope_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"StoredFile {self.id} ({self.original_filename})"
