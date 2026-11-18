"""PetDetectionService — YOLO-World animal-only gatekeeper.

Every uploaded pet photo is validated BEFORE any Cloudinary write. Non-animal photos are discarded
immediately and raise NoPetDetectedError (HTTP 422). There are no strikes and no bans — the user can
simply pick another photo.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from django.conf import settings
from PIL import Image

from apps.common.exceptions import NoPetDetectedError

from .dto import DetectionResult

if TYPE_CHECKING:
    from ultralytics import YOLOWorld

logger = logging.getLogger(__name__)

# Open-vocabulary labels passed to YOLOWorld.set_classes(). The mapping keeps the
# model's specific output labels while grouping them into PawPrint animal categories.
ANIMAL_CATEGORY_BY_LABEL: dict[str, str] = {
    # Domestic pets
    "dog": "Domestic Pet",
    "cat": "Domestic Pet",
    # Zoo / exotic animals
    "lion": "Zoo / Exotic",
    "tiger": "Zoo / Exotic",
    "wolf": "Zoo / Exotic",
    "fox": "Zoo / Exotic",
    "bear": "Zoo / Exotic",
    "elephant": "Zoo / Exotic",
    "giraffe": "Zoo / Exotic",
    "zebra": "Zoo / Exotic",
    "kangaroo": "Zoo / Exotic",
    "koala": "Zoo / Exotic",
    "panda": "Zoo / Exotic",
    "monkey": "Zoo / Exotic",
    "deer": "Zoo / Exotic",
    # Reptiles
    "crocodile": "Reptile",
    "alligator": "Reptile",
    "snake": "Reptile",
    "lizard": "Reptile",
    "gecko": "Reptile",
    "iguana": "Reptile",
    "chameleon": "Reptile",
    "turtle": "Reptile",
    "tortoise": "Reptile",
    # Small mammals
    "hamster": "Small Mammal",
    "guinea pig": "Small Mammal",
    "ferret": "Small Mammal",
    "chinchilla": "Small Mammal",
    "mouse": "Small Mammal",
    "rat": "Small Mammal",
    "hedgehog": "Small Mammal",
    "sugar glider": "Small Mammal",
    "rabbit": "Small Mammal",
    # Farm animals, including farm birds
    "horse": "Farm Animal",
    "sheep": "Farm Animal",
    "cow": "Farm Animal",
    "goat": "Farm Animal",
    "pig": "Farm Animal",
    "donkey": "Farm Animal",
    "llama": "Farm Animal",
    "alpaca": "Farm Animal",
    "chicken": "Farm Animal",
    "duck": "Farm Animal",
    "goose": "Farm Animal",
    "turkey": "Farm Animal",
    # Birds
    "bird": "Bird",
    "parrot": "Bird",
    "cockatiel": "Bird",
    "parakeet": "Bird",
    "budgerigar": "Bird",
    "canary": "Bird",
    "finch": "Bird",
    "lovebird": "Bird",
    "macaw": "Bird",
    "cockatoo": "Bird",
    "pigeon": "Bird",
    "dove": "Bird",
    # Fish
    "fish": "Fish",
    "goldfish": "Fish",
    "betta fish": "Fish",
    "koi": "Fish",
    "guppy": "Fish",
    "angelfish": "Fish",
    "clownfish": "Fish",
}

ANIMAL_CLASSES: tuple[str, ...] = tuple(ANIMAL_CATEGORY_BY_LABEL)
DEFAULT_YOLO_WORLD_MODEL = "yolov8s-worldv2.pt"

_MODEL: YOLOWorld | None = None
_MODEL_LOCK = Lock()


def _resolve_world_model_path(path: str) -> str:
    """Return a YOLO-World checkpoint path, replacing stale non-World paths."""
    if "world" not in Path(path).name.lower():
        logger.warning(
            "YOLO_MODEL_PATH=%r is not a YOLO-World checkpoint; using %r",
            path,
            DEFAULT_YOLO_WORLD_MODEL,
        )
        return DEFAULT_YOLO_WORLD_MODEL
    return path


def _get_model() -> YOLOWorld:
    """Lazily load, configure, and cache one YOLO-World model per process."""
    global _MODEL
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:
                from ultralytics import YOLOWorld

                model_path = _resolve_world_model_path(settings.YOLO_MODEL_PATH)
                model = YOLOWorld(model_path)
                if not hasattr(getattr(model, "model", None), "set_classes"):
                    raise RuntimeError(
                        f"YOLO-World checkpoint required at {model_path!r}; "
                        f"loaded {type(getattr(model, 'model', model)).__name__}. "
                        f"Set YOLO_MODEL_PATH={DEFAULT_YOLO_WORLD_MODEL}."
                    )
                model.set_classes(list(ANIMAL_CLASSES))
                _MODEL = model
    return _MODEL


class PetDetectionService:
    """Validates that an image contains an animal from the configured categories."""

    def validate_pet_image(self, image_bytes: bytes) -> DetectionResult:
        """Run YOLO-World over the image; return pass/fail plus detected labels.

        Raises NoPetDetectedError when no configured animal clears the confidence threshold.
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
                label = str(names[int(cls_id)]).strip().lower()
                max_confidence = max(max_confidence, float(conf))
                if label not in detected_classes:
                    detected_classes.append(label)
                if (
                    label in ANIMAL_CATEGORY_BY_LABEL
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
