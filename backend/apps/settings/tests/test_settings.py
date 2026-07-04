import json
from unittest.mock import Mock, patch

from apps.settings.domain.models import InstitutionSetting, SettingValueType, UserSetting
from apps.settings.services.settings_service import SettingsService


class DummyUser:
    id = "user-1"


class DummyInstitution:
    id = "institution-1"


def test_create_and_update_user_setting():
    publisher = Mock()
    service = SettingsService(event_publisher=publisher)
    user = DummyUser()

    with patch("apps.settings.services.settings_service.UserSetting.objects") as user_objects:
        user_objects.update_or_create.return_value = (Mock(), True)
        setting = service.set_user_setting(user, "theme", "dark")

    assert setting is not None
    publisher.publish.assert_called_once()
    event = publisher.publish.call_args.args[0]
    assert event.event_name == "settings.user_setting_changed"


def test_get_user_setting_returns_default_when_missing():
    service = SettingsService(event_publisher=Mock())
    user = DummyUser()

    with patch("apps.settings.services.settings_service.UserSetting.objects") as user_objects:
        user_objects.get.side_effect = UserSetting.DoesNotExist
        value = service.get_user_setting(user, "missing", default="fallback")

    assert value == "fallback"


def test_delete_user_setting_publishes_event():
    publisher = Mock()
    service = SettingsService(event_publisher=publisher)
    user = DummyUser()

    with patch("apps.settings.services.settings_service.UserSetting.objects") as user_objects:
        user_objects.filter.return_value.delete.return_value = (1, {})
        service.delete_user_setting(user, "theme")

    publisher.publish.assert_called_once()
    event = publisher.publish.call_args.args[0]
    assert event.event_name == "settings.user_setting_deleted"


def test_create_and_update_institution_setting():
    publisher = Mock()
    service = SettingsService(event_publisher=publisher)
    institution = DummyInstitution()

    with patch("apps.settings.services.settings_service.InstitutionSetting.objects") as institution_objects:
        institution_objects.update_or_create.return_value = (Mock(), True)
        setting = service.set_institution_setting(institution, "timezone", "Europe/London")

    assert setting is not None
    publisher.publish.assert_called_once()
    event = publisher.publish.call_args.args[0]
    assert event.event_name == "settings.institution_setting_changed"


def test_get_institution_setting_returns_default_when_missing():
    service = SettingsService(event_publisher=Mock())
    institution = DummyInstitution()

    with patch("apps.settings.services.settings_service.InstitutionSetting.objects") as institution_objects:
        institution_objects.get.side_effect = InstitutionSetting.DoesNotExist
        value = service.get_institution_setting(institution, "missing", default="fallback")

    assert value == "fallback"


def test_delete_institution_setting_publishes_event():
    publisher = Mock()
    service = SettingsService(event_publisher=publisher)
    institution = DummyInstitution()

    with patch("apps.settings.services.settings_service.InstitutionSetting.objects") as institution_objects:
        institution_objects.filter.return_value.delete.return_value = (1, {})
        service.delete_institution_setting(institution, "timezone")

    publisher.publish.assert_called_once()
    event = publisher.publish.call_args.args[0]
    assert event.event_name == "settings.institution_setting_deleted"


def test_value_type_serialization_and_deserialization():
    service = SettingsService(event_publisher=Mock())

    assert service._serialize_value("hello")[1] == SettingValueType.STRING
    assert service._serialize_value(5, SettingValueType.INTEGER) == ("5", SettingValueType.INTEGER)
    assert service._serialize_value(True, SettingValueType.BOOLEAN) == ("true", SettingValueType.BOOLEAN)
    assert service._serialize_value({"a": 1}, SettingValueType.JSON) == (json.dumps({"a": 1}), SettingValueType.JSON)
    assert service._deserialize_value("5", SettingValueType.INTEGER) == 5
    assert service._deserialize_value("true", SettingValueType.BOOLEAN) is True
    assert service._deserialize_value(json.dumps({"a": 1}), SettingValueType.JSON) == {"a": 1}


def test_unique_constraints_are_defined():
    assert UserSetting._meta.unique_together == (("user", "key"),)
    assert InstitutionSetting._meta.unique_together == (("institution", "key"),)
