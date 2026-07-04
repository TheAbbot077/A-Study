from unittest.mock import Mock, patch

from apps.audit.domain.models import AuditEntry
from apps.audit.services.audit_service import AuditService


class DummyUser:
    id = "user-1"


class DummyInstitution:
    id = "institution-1"


def test_record_action_with_actor_and_metadata():
    publisher = Mock()
    service = AuditService(event_publisher=publisher)
    actor = DummyUser()

    with patch("apps.audit.services.audit_service.AuditEntry.objects") as audit_objects:
        fake_entry = Mock(spec=AuditEntry)
        fake_entry.id = "entry-1"
        fake_entry.action = "user.login"
        fake_entry.target_type = "user"
        fake_entry.target_id = "user-1"
        audit_objects.create.return_value = fake_entry

        entry = service.record_action(
            actor=actor,
            action="user.login",
            target_type="user",
            target_id="user-1",
            target_display="demo",
            metadata={"ip": "127.0.0.1"},
        )

    assert entry is fake_entry
    publisher.publish.assert_called_once()
    event = publisher.publish.call_args.args[0]
    assert event.event_name == "audit.entry_recorded"


def test_record_action_without_actor():
    publisher = Mock()
    service = AuditService(event_publisher=publisher)

    with patch("apps.audit.services.audit_service.AuditEntry.objects") as audit_objects:
        fake_entry = Mock(spec=AuditEntry)
        fake_entry.id = "entry-2"
        fake_entry.action = "system.started"
        fake_entry.target_type = ""
        fake_entry.target_id = ""
        audit_objects.create.return_value = fake_entry
        service.record_action(action="system.started")

    publisher.publish.assert_called_once()


def test_record_action_with_institution():
    publisher = Mock()
    service = AuditService(event_publisher=publisher)
    institution = DummyInstitution()

    with patch("apps.audit.services.audit_service.AuditEntry.objects") as audit_objects:
        fake_entry = Mock(spec=AuditEntry)
        fake_entry.id = "entry-3"
        fake_entry.action = "institution.created"
        fake_entry.target_type = "institution"
        fake_entry.target_id = "institution-1"
        audit_objects.create.return_value = fake_entry
        service.record_action(institution=institution, action="institution.created", target_type="institution", target_id="institution-1")

    publisher.publish.assert_called_once()


def test_list_for_actor_and_institution_and_target():
    service = AuditService(event_publisher=Mock())
    actor = DummyUser()
    institution = DummyInstitution()
    expected_entries = [Mock()]

    with patch("apps.audit.services.audit_service.AuditEntry.objects") as audit_objects:
        audit_objects.filter.return_value.order_by.return_value = expected_entries
        actor_entries = service.list_for_actor(actor)
        institution_entries = service.list_for_institution(institution)
        target_entries = service.list_for_target("user", "user-1")

    assert actor_entries == expected_entries
    assert institution_entries == expected_entries
    assert target_entries == expected_entries
