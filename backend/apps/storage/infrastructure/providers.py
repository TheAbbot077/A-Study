import hashlib
import os
import uuid
from typing import BinaryIO, Protocol, runtime_checkable

from django.conf import settings


@runtime_checkable
class StorageProvider(Protocol):
    def upload(self, content: BinaryIO, original_filename: str, content_type: str | None = None) -> dict:
        ...

    def download(self, stored_filename: str) -> BinaryIO:
        ...

    def delete(self, stored_filename: str) -> None:
        ...

    def exists(self, stored_filename: str) -> bool:
        ...

    def generate_url(self, stored_filename: str) -> str:
        ...


class LocalStorageProvider:
    def __init__(self, base_path: str | None = None) -> None:
        self.base_path = base_path or settings.MEDIA_ROOT
        os.makedirs(self.base_path, exist_ok=True)

    def _path_for(self, stored_filename: str) -> str:
        return os.path.join(self.base_path, stored_filename)

    def upload(self, content: BinaryIO, original_filename: str, content_type: str | None = None) -> dict:
        # generate a unique filename
        ext = os.path.splitext(original_filename)[1]
        stored_filename = f"{uuid.uuid4().hex}{ext}"
        path = self._path_for(stored_filename)

        # read and write
        hasher = hashlib.sha256()
        size = 0
        with open(path, "wb") as out_f:
            # support file-like that yields bytes via read()
            chunk = content.read(8192)
            while chunk:
                if isinstance(chunk, str):
                    chunk = chunk.encode()
                out_f.write(chunk)
                hasher.update(chunk)
                size += len(chunk)
                chunk = content.read(8192)

        return {
            "stored_filename": stored_filename,
            "size_bytes": size,
            "checksum": hasher.hexdigest(),
            "provider": "local",
        }

    def download(self, stored_filename: str) -> BinaryIO:
        path = self._path_for(stored_filename)
        return open(path, "rb")

    def delete(self, stored_filename: str) -> None:
        path = self._path_for(stored_filename)
        if os.path.exists(path):
            os.remove(path)

    def exists(self, stored_filename: str) -> bool:
        return os.path.exists(self._path_for(stored_filename))

    def generate_url(self, stored_filename: str) -> str:
        # non-signed, server-relative
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        return os.path.join(media_url.rstrip("/"), stored_filename)
