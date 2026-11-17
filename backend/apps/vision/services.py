"""PetDetectionService — YOLOv8 pet-only gatekeeper.

Every uploaded photo is validated BEFORE any S3 write. Non-pet photos are discarded
immediately and raise NoPetDetectedError (HTTP 422). There are no strikes and no bans —
the user can simply pick another photo.
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

from django.conf import settings
from PIL import Image

from apps.common.exceptions import NoPetDetectedError

from .dto import DetectionResult

if TYPE_CHECKING:
    from ultralytics import YOLO

logger = logging.getLogger(__name__)

_MODEL: YOLO | None = None


def _get_model() -> YOLO:
    """Singleton, lazily-loaded YOLOv8 model instance."""
    global _MODEL
    if _MODEL is None:
        from ultralytics import YOLO

        _MODEL = YOLO(settings.YOLO_MODEL_PATH)
    return _MODEL


class PetDetectionService:
    """Validates that an image contains a pet (COCO animal classes)."""

    def validate_pet_image(self, image_bytes: bytes) -> DetectionResult:
        """Run YOLOv8 over the image; return pass/fail plus detected labels.

        Raises NoPetDetectedError when no pet class clears the confidence threshold.
        """
        model = _get_model()
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        results = model.predict(image, verbose=False)
        pet_classes: list[str] = []
        detected_classes: list[str] = []
        max_confidence = 0.0
        for result in results:
            if not hasattr(result, "names") or not hasattr(result, "boxes"):
                continue
            names = result.names
            boxes = result.boxes
            if boxes is None:
                continue
            for cls_id, conf in zip(boxes.cls.tolist(), boxes.conf.tolist(), strict=True):
                label = str(names[int(cls_id)])
                max_confidence = max(max_confidence, float(conf))
                if label not in detected_classes:
                    detected_classes.append(label)
                if (
                    int(cls_id) in settings.YOLO_PET_CLASS_IDS
                    and float(conf) >= settings.YOLO_CONFIDENCE_THRESHOLD
                    and label not in pet_classes
                ):
                    pet_classes.append(label)
        passed = bool(pet_classes)
        detection = DetectionResult(
            passed=passed,
            pet_classes=pet_classes,
            detected_classes=detected_classes,
            max_confidence=max_confidence,
        )
        if not passed:
            raise NoPetDetectedError(detected_labels=detected_classes)
        return detection

    @staticmethod
    def strip_exif(image_bytes: bytes) -> bytes:
        """Re-encode the image through Pillow, dropping all EXIF metadata."""
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90, optimize=True)
        return buffer.getvalue()

    @staticmethod
    def make_thumbnail(image_bytes: bytes, size: tuple[int, int] = (320, 320)) -> bytes:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        image.thumbnail(size, Image.Resampling.LANCZOS)
        if image.mode != "RGB":
            image = image.convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=80, optimize=True)
        return buffer.getvalue()

    @staticmethod
    def record_detection(user, detection: DetectionResult, passed: bool):  # noqa: ANN001, ANN202
        """Persist a PetDetectionLog row (audit only — never a penalty)."""
        from .models import PetDetectionLog

        return PetDetectionLog.objects.create(
            user=user,
            detected_classes=detection.detected_classes,
            max_confidence=detection.max_confidence,
            passed=passed,
        )
