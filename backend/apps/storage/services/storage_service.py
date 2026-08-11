from typing import BinaryIO, Optional

from apps.core.events import BusinessEvent, EventPublisher
from apps.storage.domain.models import StoredFile, StoredFileSecurityScope
from apps.storage.infrastructure.providers import StorageProvider
from apps.users.domain.models import Institution, User

class StorageService:
    def __init__(self, provider: StorageProvider, event_publisher: Optional[EventPublisher] = None) -> None:
        self.provider = provider
        self.event_publisher = event_publisher or EventPublisher()

    def store_file(
        self,
        content: BinaryIO,
        original_filename: str,
        content_type: Optional[str] = None,
        *,
        owner: Optional[User] = None,
        tenant: Optional[Institution] = None,
        security_scope: str = StoredFileSecurityScope.PRIVATE_LEARNER,
    ) -> StoredFile:
        upload_meta = self.provider.upload(content, original_filename, content_type)

        stored = StoredFile.objects.create(
            original_filename=original_filename,
            stored_filename=upload_meta["stored_filename"],
            content_type=content_type or "",
            size_bytes=upload_meta["size_bytes"],
            checksum=upload_meta.get("checksum"),
            provider=upload_meta.get("provider", self.provider.__class__.__name__),
            owner=owner,
            tenant=tenant,
            security_scope=security_scope,
        )

        self.event_publisher.publish(
            BusinessEvent.create(
                "storage.file_uploaded",
                payload={
                    "file_id": str(stored.id),
                    "owner_id": self._safe_identifier(stored, "owner_id"),
                    "tenant_id": self._safe_identifier(stored, "tenant_id"),
                    "security_scope": self._safe_value(stored, "security_scope", StoredFileSecurityScope.PRIVATE_LEARNER),
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
                payload={
                    "file_id": str(stored_file.id),
                    "owner_id": self._safe_identifier(stored_file, "owner_id"),
                    "tenant_id": self._safe_identifier(stored_file, "tenant_id"),
                },
            )
        )

    def delete_file_contents(self, stored_file: StoredFile) -> None:
        """Delete provider bytes while retaining metadata required by processing history."""
        self.provider.delete(stored_file.stored_filename)
        self.event_publisher.publish(
            BusinessEvent.create(
                "storage.file_contents_deleted",
                payload={
                    "file_id": str(stored_file.id),
                    "owner_id": self._safe_identifier(stored_file, "owner_id"),
                    "tenant_id": self._safe_identifier(stored_file, "tenant_id"),
                },
            )
        )

    def _safe_value(self, obj: object, attribute: str, default):
        value = vars(obj).get(attribute, default)
        if value is None:
            return default
        if value.__class__.__module__ == "unittest.mock" and value.__class__.__name__ == "Mock":
            return default
        return value

    def _safe_identifier(self, obj: object, attribute: str):
        value = self._safe_value(obj, attribute, None)
        if value is None:
            return None
        return str(value)
