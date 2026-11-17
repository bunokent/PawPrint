"""Pet services — writes and the photo-upload pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.db import transaction

from apps.common import storage
from apps.common.exceptions import NoPetDetectedError
from apps.vision.services import PetDetectionService

from .models import Pet


@dataclass(frozen=True)
class UploadedPhoto:
    key: str
    url: str
    thumb_key: str
    thumb_url: str
    pet_classes: list[str]
    detected_classes: list[str]
    max_confidence: float


class PetService:
    """Pet writes."""

    @staticmethod
    @transaction.atomic
    def create_pet(owner, *, name: str, species: str = "dog", breed: str = "", color: str = "",
                   age: int | None = None, temperament_tags: list[str] | None = None,
                   health_tags: list[str] | None = None, photo_path: str = "",
                   status: str = Pet.Status.ADOPTABLE) -> Pet:
        return Pet.objects.create(
            owner=owner, name=name, species=species, breed=breed, color=color, age=age,
            temperament_tags=temperament_tags or [], health_tags=health_tags or [],
            photo_path=photo_path, status=status,
        )


class PetPhotoService:
    """Photo upload pipeline: YOLOv8 gate → EXIF strip → private S3 → thumbnail task."""

    detection = PetDetectionService()

    @classmethod
    def upload(cls, user, filename: str, image_bytes: bytes) -> UploadedPhoto:
        """NOT wrapped in a transaction: a rejected photo must still leave its audit log."""
        """Validate + store a pet photo. Raises NoPetDetectedError (422) for non-pet images.

        The bytes are NEVER written to S3 when detection fails.
        """
        try:
            detection = cls.detection.validate_pet_image(image_bytes)
        except NoPetDetectedError as exc:
            cls.detection.record_detection(user, _as_result(exc), passed=False)
            raise
        cls.detection.record_detection(user, detection, passed=True)

        clean = cls.detection.strip_exif(image_bytes)
        photo_id = uuid.uuid4()
        key = f"pets/photos/{user.pk}/{photo_id}.jpg"
        thumb_key = f"pets/photos/{user.pk}/{photo_id}_thumb.jpg"
        storage.upload_bytes(key, clean, content_type="image/jpeg")
        from .tasks import generate_thumbnail

        generate_thumbnail.delay(key, thumb_key)
        return UploadedPhoto(
            key=key,
            url=storage.signed_url(key),
            thumb_key=thumb_key,
            thumb_url=storage.signed_url(thumb_key),
            pet_classes=detection.pet_classes,
            detected_classes=detection.detected_classes,
            max_confidence=detection.max_confidence,
        )


def _as_result(exc: NoPetDetectedError):
    from apps.vision.dto import DetectionResult

    return DetectionResult(
        passed=False,
        pet_classes=[],
        detected_classes=exc.detected_labels,
        max_confidence=0.0,
    )
