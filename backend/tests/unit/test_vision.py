"""Unit: PetDetectionService (YOLO-World gatekeeper) with a mocked model."""

import io

import pytest
from PIL import Image

from apps.common.exceptions import NoPetDetectedError
from apps.vision.dto import DetectionResult
from apps.vision.models import PetDetectionLog
from apps.vision.services import ANIMAL_CATEGORY_BY_LABEL, PetDetectionService

pytestmark = pytest.mark.django_db


def _img_bytes() -> bytes:
    img = Image.new("RGB", (32, 32), (10, 200, 10))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class _FakeBoxes:
    def __init__(self, cls_ids, confs):
        import numpy as np

        self.cls = np.array(cls_ids, dtype=float)
        self.conf = np.array(confs, dtype=float)


class _FakeResult:
    def __init__(self, names, boxes):
        self.names = names
        self.boxes = boxes


def _mock_model(monkeypatch, detections, label_overrides=None):
    """detections: list of (cls_id, conf); label_overrides maps ids to open-vocabulary labels."""
    names = {i: f"cls{i}" for i in range(80)}
    names.update({14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow", 0: "person"})
    names.update(label_overrides or {})
    boxes = _FakeBoxes([c for c, _ in detections], [f for _, f in detections])

    class FakeModel:
        def predict(self, image, verbose=False):
            return [_FakeResult(names, boxes)]

    monkeypatch.setattr("apps.vision.services._get_model", lambda: FakeModel())


def test_detects_dog_passes(monkeypatch):
    _mock_model(monkeypatch, [(16, 0.92), (0, 0.5)])
    result = PetDetectionService().validate_pet_image(_img_bytes())
    assert result.passed is True
    assert result.pet_classes == ["dog"]
    assert "person" in result.detected_classes
    assert result.max_confidence == pytest.approx(0.92)


def test_detects_cat_below_threshold_fails(monkeypatch, settings):
    settings.YOLO_CONFIDENCE_THRESHOLD = 0.45
    _mock_model(monkeypatch, [(15, 0.30)])
    with pytest.raises(NoPetDetectedError) as exc_info:
        PetDetectionService().validate_pet_image(_img_bytes())
    assert exc_info.value.status_code == 422
    assert exc_info.value.detected_labels == ["cat"]


def test_non_pet_rejected_with_labels(monkeypatch):
    _mock_model(monkeypatch, [(0, 0.99), (2, 0.8)])
    with pytest.raises(NoPetDetectedError):
        PetDetectionService().validate_pet_image(_img_bytes())


def test_malformed_model_result_is_ignored(monkeypatch):
    class FakeModel:
        def predict(self, image, verbose=False):
            return [object()]

    monkeypatch.setattr("apps.vision.services._get_model", lambda: FakeModel())
    with pytest.raises(NoPetDetectedError):
        PetDetectionService().validate_pet_image(_img_bytes())


def test_bird_counts_as_pet(monkeypatch):
    _mock_model(monkeypatch, [(14, 0.6)])
    assert PetDetectionService().validate_pet_image(_img_bytes()).passed is True


@pytest.mark.parametrize(
    ("label", "category"),
    [
        ("lion", "Zoo / Exotic"),
        ("crocodile", "Reptile"),
        ("sugar glider", "Small Mammal"),
        ("goat", "Farm Animal"),
        ("cockatiel", "Bird"),
        ("goldfish", "Fish"),
        ("dog", "Domestic Pet"),
    ],
)
def test_expanded_animal_labels_pass_at_point_twenty(monkeypatch, settings, label, category):
    settings.YOLO_CONFIDENCE_THRESHOLD = 0.20
    _mock_model(monkeypatch, [(0, 0.20)], {0: label})
    result = PetDetectionService().validate_pet_image(_img_bytes())
    assert result.passed is True
    assert result.pet_classes == [label]
    assert ANIMAL_CATEGORY_BY_LABEL[label] == category


@pytest.mark.parametrize(
    ("category", "labels"),
    [
        (
            "Zoo / Exotic",
            [
                "lion", "tiger", "wolf", "fox", "bear", "elephant", "giraffe",
                "zebra", "kangaroo", "koala", "panda", "monkey", "deer",
            ],
        ),
        (
            "Reptile",
            ["crocodile", "alligator", "snake", "lizard", "gecko", "iguana", "chameleon", "turtle", "tortoise"],
        ),
        (
            "Small Mammal",
            ["hamster", "guinea pig", "ferret", "chinchilla", "mouse", "rat", "hedgehog", "sugar glider", "rabbit"],
        ),
    ],
)
def test_required_animal_category_mapping(category, labels):
    assert {label: ANIMAL_CATEGORY_BY_LABEL[label] for label in labels} == dict.fromkeys(labels, category)


def test_domestic_farm_bird_and_fish_categories_are_configured():
    expected = {
        "cat": "Domestic Pet",
        "horse": "Farm Animal",
        "chicken": "Farm Animal",
        "parrot": "Bird",
        "bird": "Bird",
        "fish": "Fish",
        "koi": "Fish",
    }
    assert {label: ANIMAL_CATEGORY_BY_LABEL[label] for label in expected} == expected


def test_strip_exif_removes_metadata():
    img = Image.new("RGB", (16, 16))
    exif = Image.Exif()
    exif[0x010F] = "TestCamera"  # Make
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw = buf.getvalue()
    cleaned = PetDetectionService.strip_exif(raw)
    out = Image.open(io.BytesIO(cleaned))
    assert not out.getexif()


def test_make_thumbnail():
    thumb = PetDetectionService.make_thumbnail(_img_bytes(), size=(320, 320))
    out = Image.open(io.BytesIO(thumb))
    assert max(out.size) <= 320


def test_record_detection(user):
    log = PetDetectionService.record_detection(
        user, DetectionResult(passed=True, pet_classes=["dog"], detected_classes=["dog"], max_confidence=0.9), True
    )
    assert isinstance(log, PetDetectionLog)
    assert log.passed is True
    assert log.user == user
