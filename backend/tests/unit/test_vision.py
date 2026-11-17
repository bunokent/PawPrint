"""Unit: PetDetectionService (YOLOv8 gatekeeper) with a mocked model."""

import io

import pytest
from PIL import Image

from apps.common.exceptions import NoPetDetectedError
from apps.vision.dto import DetectionResult
from apps.vision.models import PetDetectionLog
from apps.vision.services import PetDetectionService

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


def _mock_model(monkeypatch, detections):
    """detections: list of (cls_id, conf)"""
    names = {i: f"cls{i}" for i in range(80)}
    names.update({14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow", 0: "person"})
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


def test_bird_counts_as_pet(monkeypatch):
    _mock_model(monkeypatch, [(14, 0.6)])
    assert PetDetectionService().validate_pet_image(_img_bytes()).passed is True


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
