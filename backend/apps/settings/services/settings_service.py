import json
from typing import Any, Optional

from apps.core.events import BusinessEvent, EventPublisher
from apps.settings.domain.models import InstitutionSetting, SettingValueType, UserSetting


class SettingsService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def _infer_value_type(self, value: Any) -> str:
        if isinstance(value, bool):
            return SettingValueType.BOOLEAN
        if isinstance(value, int) and not isinstance(value, bool):
            return SettingValueType.INTEGER
        if isinstance(value, (dict, list)):
            return SettingValueType.JSON
        return SettingValueType.STRING

    def _serialize_value(self, value: Any, value_type: Optional[str] = None) -> tuple[Any, str]:
        resolved_type = value_type or self._infer_value_type(value)
        if resolved_type == SettingValueType.INTEGER:
            return str(value), resolved_type
        if resolved_type == SettingValueType.BOOLEAN:
            return str(bool(value)).lower(), resolved_type
        if resolved_type == SettingValueType.JSON:
            return json.dumps(value), resolved_type
        return str(value), resolved_type

    def _deserialize_value(self, value: str, value_type: str) -> Any:
        if value_type == SettingValueType.INTEGER:
            return int(value)
        if value_type == SettingValueType.BOOLEAN:
            return value.lower() == "true"
        if value_type == SettingValueType.JSON:
            return json.loads(value)
        return value

    def set_user_setting(self, user, key: str, value: Any, value_type: Optional[str] = None) -> UserSetting:
        serialized_value, resolved_type = self._serialize_value(value, value_type)
        setting, created = UserSetting.objects.update_or_create(
            user=user,
            key=key,
            defaults={"value": serialized_value, "value_type": resolved_type},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "settings.user_setting_changed",
                payload={"user_id": str(user.id), "key": key, "value_type": resolved_type},
            )
        )
        return setting

    def get_user_setting(self, user, key: str, default: Any = None) -> Any:
        try:
            setting = UserSetting.objects.get(user=user, key=key)
        except UserSetting.DoesNotExist:
            return default
        return self._deserialize_value(setting.value, setting.value_type)

    def delete_user_setting(self, user, key: str) -> None:
        deleted = UserSetting.objects.filter(user=user, key=key).delete()[0]
        if deleted:
            self.event_publisher.publish(
                BusinessEvent.create(
                    "settings.user_setting_deleted",
                    payload={"user_id": str(user.id), "key": key},
                )
            )

    def set_institution_setting(self, institution, key: str, value: Any, value_type: Optional[str] = None) -> InstitutionSetting:
        serialized_value, resolved_type = self._serialize_value(value, value_type)
        setting, created = InstitutionSetting.objects.update_or_create(
            institution=institution,
            key=key,
            defaults={"value": serialized_value, "value_type": resolved_type},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "settings.institution_setting_changed",
                payload={"institution_id": str(institution.id), "key": key, "value_type": resolved_type},
            )
        )
        return setting

    def get_institution_setting(self, institution, key: str, default: Any = None) -> Any:
        try:
            setting = InstitutionSetting.objects.get(institution=institution, key=key)
        except InstitutionSetting.DoesNotExist:
            return default
        return self._deserialize_value(setting.value, setting.value_type)

    def delete_institution_setting(self, institution, key: str) -> None:
        deleted = InstitutionSetting.objects.filter(institution=institution, key=key).delete()[0]
        if deleted:
            self.event_publisher.publish(
                BusinessEvent.create(
                    "settings.institution_setting_deleted",
                    payload={"institution_id": str(institution.id), "key": key},
                )
            )
