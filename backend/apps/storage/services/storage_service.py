import hashlib
import logging
import os
from typing import BinaryIO, Optional

from django.conf import settings

from apps.core.events import BusinessEvent, EventPublisher
from apps.storage.domain.models import StoredFile
from apps.storage.infrastructure.providers import StorageProvider

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, provider: StorageProvider, event_publisher: Optional[EventPublisher] = None) -> None:
        self.provider = provider
        self.event_publisher = event_publisher or EventPublisher()

    def store_file(self, content: BinaryIO, original_filename: str, content_type: Optional[str] = None) -> StoredFile:
        upload_meta = self.provider.upload(content, original_filename, content_type)

        stored = StoredFile.objects.create(
            original_filename=original_filename,
            stored_filename=upload_meta["stored_filename"],
            content_type=content_type or "",
            size_bytes=upload_meta["size_bytes"],
            checksum=upload_meta.get("checksum"),
            provider=upload_meta.get("provider", self.provider.__class__.__name__),
        )

        self.event_publisher.publish(
            BusinessEvent.create(
                "storage.file_uploaded",
                payload={
                    "file_id": str(stored.id),
                    "original_filename": stored.original_filename,
                    "stored_filename": stored.stored_filename,
                    "provider": stored.provider,
                },
            )
        )

        return stored

    def retrieve_file(self, stored_filename: str) -> BinaryIO:
        return self.provider.download(stored_filename)

    def delete_file(self, stored_file: StoredFile) -> None:
        # delete from provider first
        self.provider.delete(stored_file.stored_filename)
        StoredFile.objects.filter(id=stored_file.id).delete()

        self.event_publisher.publish(
            BusinessEvent.create(
                "storage.file_deleted",
                payload={"file_id": str(stored_file.id), "stored_filename": stored_file.stored_filename},
            )
        )
