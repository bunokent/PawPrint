"""Pet tasks (queue: images)."""

from __future__ import annotations

from celery import shared_task

from apps.common import storage
from apps.vision.services import PetDetectionService


@shared_task(name="apps.pets.tasks.generate_thumbnail")
def generate_thumbnail(photo_key: str, thumb_key: str) -> str:
    """Generate a 320px thumbnail for an already-stored photo."""
    raw = storage.read_bytes(photo_key)
    thumb = PetDetectionService.make_thumbnail(raw)
    storage.upload_bytes(thumb_key, thumb, content_type="image/jpeg")
    return thumb_key
