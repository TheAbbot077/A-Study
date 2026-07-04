import json
import uuid
from typing import Any

from django.db import models

from apps.users.domain.models import Institution, User


class SettingValueType(models.TextChoices):
    STRING = "string", "String"
    INTEGER = "integer", "Integer"
    BOOLEAN = "boolean", "Boolean"
    JSON = "json", "JSON"


class UserSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="settings")
    key = models.CharField(max_length=255)
    value = models.TextField()
    value_type = models.CharField(max_length=50, choices=SettingValueType.choices, default=SettingValueType.STRING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settings_user_setting"
        unique_together = (("user", "key"),)
        ordering = ["-updated_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"UserSetting {self.key} for {self.user_id}"


class InstitutionSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="settings")
    key = models.CharField(max_length=255)
    value = models.TextField()
    value_type = models.CharField(max_length=50, choices=SettingValueType.choices, default=SettingValueType.STRING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settings_institution_setting"
        unique_together = (("institution", "key"),)
        ordering = ["-updated_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"InstitutionSetting {self.key} for {self.institution_id}"
