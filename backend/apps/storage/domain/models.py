import uuid
from django.db import models


class StoredFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_filename = models.CharField(max_length=512)
    stored_filename = models.CharField(max_length=512)
    content_type = models.CharField(max_length=128, blank=True, null=True)
    size_bytes = models.BigIntegerField()
    checksum = models.CharField(max_length=128, blank=True, null=True)
    provider = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "storage_storedfile"
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"StoredFile {self.id} ({self.original_filename})"
