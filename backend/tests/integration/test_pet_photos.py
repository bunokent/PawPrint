"""Integration: YOLOv8-gated photo upload endpoint."""

import io

import pytest
from PIL import Image

from apps.vision.dto import DetectionResult
from apps.vision.models import PetDetectionLog

pytestmark = pytest.mark.django_db


def _png_bytes(color=(200, 30, 30)) -> bytes:
    img = Image.new("RGB", (64, 64), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _mock_detection_pass(monkeypatch):
    result = DetectionResult(
        passed=True, pet_classes=["dog"], detected_classes=["dog"], max_confidence=0.91
    )
    monkeypatch.setattr(
        "apps.pets.services.PetPhotoService.detection.validate_pet_image", lambda b: result
    )
    return result


def test_upload_pet_photo_success(auth_client, monkeypatch):
    _mock_detection_pass(monkeypatch)
    resp = auth_client.post(
        "/api/pets/photos", {"photo": io.BytesIO(_png_bytes()), "name": "pet.png"},
        format="multipart",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["pet_classes"] == ["dog"]
    assert body["key"].startswith("pets/photos/")
    assert body["url"]
    # detection logged as passed
    assert PetDetectionLog.objects.filter(passed=True).count() == 1


def test_upload_non_pet_photo_422(auth_client, monkeypatch):
    from apps.common.exceptions import NoPetDetectedError

    def fail(b):
        raise NoPetDetectedError(detected_labels=["person", "car"])

    monkeypatch.setattr(
        "apps.pets.services.PetPhotoService.detection.validate_pet_image", fail
    )
    resp = auth_client.post(
        "/api/pets/photos", {"photo": io.BytesIO(_png_bytes((30, 30, 200))), "name": "car.png"},
        format="multipart",
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "no_pet_detected"
    assert "No pet detected" in body["error"]["message"]
    assert body["error"]["detected_labels"] == ["person", "car"]
    # logged as failed, and no storage object was written (zero penalties, just a log)
    assert PetDetectionLog.objects.filter(passed=False).count() == 1
    from django.core.files.storage import default_storage

    assert not any(default_storage.listdir("pets")[1]) if default_storage.exists("pets") else True


def test_upload_requires_auth(api_client):
    resp = api_client.post(
        "/api/pets/photos", {"photo": io.BytesIO(_png_bytes()), "name": "x.png"}, format="multipart"
    )
    assert resp.status_code == 401


def test_upload_missing_file_400(auth_client):
    resp = auth_client.post("/api/pets/photos", {}, format="multipart")
    assert resp.status_code == 400


def test_upload_throttle_10_per_min(auth_client, monkeypatch):
    _mock_detection_pass(monkeypatch)
    for _ in range(10):
        resp = auth_client.post(
            "/api/pets/photos", {"photo": io.BytesIO(_png_bytes()), "name": "p.png"}, format="multipart"
        )
        assert resp.status_code == 201
    resp = auth_client.post(
        "/api/pets/photos", {"photo": io.BytesIO(_png_bytes()), "name": "p.png"}, format="multipart"
    )
    assert resp.status_code == 429
