import io
import os
import tempfile
import uuid
from unittest.mock import Mock, patch

from django.conf import settings

from apps.storage.infrastructure.providers import LocalStorageProvider, StorageProvider
from apps.storage.services.storage_service import StorageService
from apps.storage.domain.models import StoredFile


def test_local_provider_upload_and_download_and_delete(tmp_path, monkeypatch):
    media_root = tmp_path / "media"
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(media_root))
    provider = LocalStorageProvider()

    content = io.BytesIO(b"hello world")
    meta = provider.upload(content, "greeting.txt", "text/plain")

    assert "stored_filename" in meta
    assert provider.exists(meta["stored_filename"]) is True

    f = provider.download(meta["stored_filename"]) 
    data = f.read()
    f.close()
    assert data == b"hello world"

    provider.delete(meta["stored_filename"])
    assert provider.exists(meta["stored_filename"]) is False


def test_storage_service_stores_and_publishes(monkeypatch):
    # prepare a fake provider and publisher
    provider = Mock(spec=StorageProvider)
    provider.upload.return_value = {
        "stored_filename": "abc123",
        "size_bytes": 11,
        "checksum": "deadbeef",
        "provider": "local",
    }

    publisher = Mock()
    service = StorageService(provider=provider, event_publisher=publisher)

    # patch StoredFile.objects.create to avoid DB dependency
    fake_file = Mock()
    fake_file.id = uuid.uuid4()
    fake_file.stored_filename = "abc123"
    fake_file.original_filename = "greeting.txt"
    fake_file.provider = "local"

    with patch("apps.storage.services.storage_service.StoredFile.objects") as objs:
        objs.create.return_value = fake_file
        result = service.store_file(io.BytesIO(b"hello"), "greeting.txt", "text/plain")

    assert result is fake_file
    publisher.publish.assert_called_once()
    published_event = publisher.publish.call_args.args[0]
    assert published_event.event_name == "storage.file_uploaded"


def test_storage_service_delete_publishes(monkeypatch):
    provider = Mock(spec=StorageProvider)
    publisher = Mock()
    service = StorageService(provider=provider, event_publisher=publisher)

    fake_file = Mock()
    fake_file.id = uuid.uuid4()
    fake_file.stored_filename = "abc123"

    with patch("apps.storage.services.storage_service.StoredFile.objects") as objs:
        objs.filter.return_value.delete.return_value = None
        service.delete_file(fake_file)

    provider.delete.assert_called_once_with("abc123")
    publisher.publish.assert_called_once()
    event = publisher.publish.call_args.args[0]
    assert event.event_name == "storage.file_deleted"
