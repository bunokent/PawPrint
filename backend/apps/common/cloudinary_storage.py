"""Cloudinary storage backend — private assets with signed URLs (replaces S3/MinIO).

All uploads use Cloudinary delivery type ``private``; reads/URLs are HMAC-signed
via ``cloudinary.utils.cloudinary_url(..., sign_url=True)`` so nothing is publicly
accessible without a short-lived signature.
"""

from __future__ import annotations

import time
from typing import IO

import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils
import httpx
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf")


def configure_cloudinary() -> None:
    """Configure the SDK from settings (CLOUDINARY_URL or the discrete vars)."""
    if settings.CLOUDINARY_URL:
        cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL, secure=True)
    else:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )


def resource_type_for(name: str, content_type: str = "") -> str:
    """Cloudinary groups jpg/png/webp/gif AND pdf under resource_type 'image'; rest is 'raw'."""
    if content_type in _IMAGE_TYPES or name.lower().endswith(_IMAGE_EXTS):
        return "image"
    return "raw"


class CloudinaryStorage(Storage):
    """Django ``Storage`` facade over Cloudinary private delivery."""

    def __init__(self) -> None:
        configure_cloudinary()

    def _save(self, name: str, content: IO[bytes]) -> str:
        data = content.read()
        content_type = getattr(content, "content_type", None) or "application/octet-stream"
        cloudinary.uploader.upload(
            data,
            public_id=name,
            resource_type=resource_type_for(name, content_type),
            type="private",
            overwrite=True,
            invalidate=True,
        )
        return name

    def _open(self, name: str, mode: str = "rb") -> ContentFile:
        resp = httpx.get(self.url(name), timeout=30)
        resp.raise_for_status()
        return ContentFile(resp.content, name=name)

    def delete(self, name: str) -> None:
        cloudinary.uploader.destroy(name, resource_type=resource_type_for(name), type="private")

    def exists(self, name: str) -> bool:
        try:
            cloudinary.api.resource(name, resource_type=resource_type_for(name), type="private")
        except Exception:
            return False
        return True

    def url(self, name: str | None, expire: int | None = None) -> str:
        """Signed private URL; ``expire`` seconds of validity when given."""
        if not name:
            raise ValueError("A storage name is required to build a signed URL.")
        kwargs: dict = {
            "resource_type": resource_type_for(name),
            "type": "private",
            "sign_url": True,
        }
        if expire:
            kwargs["expires_at"] = int(time.time()) + expire
        return str(cloudinary.utils.cloudinary_url(name, **kwargs))

    def size(self, name: str) -> int:
        return int(cloudinary.api.resource(name, resource_type=resource_type_for(name), type="private")["bytes"])
