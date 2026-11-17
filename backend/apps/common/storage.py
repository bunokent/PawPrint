"""Storage helpers — all objects live in a PRIVATE bucket; access via pre-signed URLs."""

from django.core.files.base import ContentFile
from django.core.files.storage import Storage, default_storage


def get_storage() -> Storage:
    return default_storage


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload bytes to the private bucket and return the storage key."""
    storage = get_storage()
    if storage.exists(key):
        storage.delete(key)
    storage.save(key, ContentFile(data, name=key))
    return key


def read_bytes(key: str) -> bytes:
    with get_storage().open(key, "rb") as fh:
        return fh.read()


def signed_url(key: str, expires: int = 3600) -> str:
    """Pre-signed URL for a private object (S3: querystring auth; FS backend: media URL)."""
    storage = get_storage()
    url = getattr(storage, "url", None)
    if url is None:
        raise RuntimeError("Storage backend has no url()")
    try:
        return url(key, expire=expires)  # type: ignore[call-arg]
    except TypeError:
        return url(key)
