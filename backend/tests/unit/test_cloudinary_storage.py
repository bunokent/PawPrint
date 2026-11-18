"""Unit tests for the Cloudinary storage driver (SDK calls mocked)."""

from __future__ import annotations

import time

import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils
import httpx
import pytest
from django.core.files.base import ContentFile

from apps.common import storage as storage_helpers
from apps.common.cloudinary_storage import (
    CloudinaryStorage,
    configure_cloudinary,
    format_for,
    resource_type_for,
)


@pytest.fixture
def fake_sdk(monkeypatch):
    calls: dict = {"upload": [], "destroy": [], "resource": [], "url": [], "config": []}

    def fake_config(**kwargs):
        calls["config"].append(kwargs)

    def fake_upload(data, **kwargs):
        calls["upload"].append({"data": data, **kwargs})
        return {"public_id": kwargs["public_id"], "resource_type": kwargs.get("resource_type", "image")}

    def fake_destroy(public_id, **kwargs):
        calls["destroy"].append({"public_id": public_id, **kwargs})
        return {"result": "ok"}

    def fake_resource(public_id, **kwargs):
        calls["resource"].append({"public_id": public_id, **kwargs})
        if public_id != "existing.jpg":
            raise Exception("not found")
        return {"bytes": 1234}

    def fake_url(public_id, **kwargs):
        calls["url"].append({"public_id": public_id, **kwargs})
        # cloudinary>=1.47 returns a (url, options) tuple
        return f"https://res.cloudinary.com/demo/signed/{public_id}", {}

    monkeypatch.setattr(cloudinary, "config", fake_config)
    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)
    monkeypatch.setattr(cloudinary.uploader, "destroy", fake_destroy)
    monkeypatch.setattr(cloudinary.api, "resource", fake_resource)
    monkeypatch.setattr(cloudinary.utils, "cloudinary_url", fake_url)
    return calls


def test_resource_type_for():
    assert resource_type_for("pets/photos/x.jpg", "image/jpeg") == "image"
    assert resource_type_for("flyers/1/flyer.pdf", "application/pdf") == "image"
    assert resource_type_for("a.png") == "image"
    assert resource_type_for("notes.txt", "text/plain") == "raw"


def test_format_for():
    assert format_for("pets/photos/x.jpg") == "jpg"
    assert format_for("flyers/1/flyer.pdf") == "pdf"
    assert format_for("a.PNG") == "png"
    assert format_for("notes") is None


def test_configure_uses_cloudinary_url(settings, fake_sdk):
    settings.CLOUDINARY_URL = "cloudinary://key:secret@mycloud"
    configure_cloudinary()
    assert fake_sdk["config"] == [{"cloudinary_url": "cloudinary://key:secret@mycloud", "secure": True}]


def test_configure_uses_discrete_vars(settings, fake_sdk):
    settings.CLOUDINARY_URL = ""
    settings.CLOUDINARY_CLOUD_NAME = "mycloud"
    settings.CLOUDINARY_API_KEY = "key"
    settings.CLOUDINARY_API_SECRET = "secret"
    configure_cloudinary()
    assert fake_sdk["config"] == [
        {"cloud_name": "mycloud", "api_key": "key", "api_secret": "secret", "secure": True}
    ]


def test_save_uploads_private_and_returns_name(settings, fake_sdk):
    settings.CLOUDINARY_URL = "cloudinary://k:s@c"
    store = CloudinaryStorage()
    name = store.save("pets/photos/abc.jpg", ContentFile(b"jpeg-bytes", name="abc.jpg"))
    assert name == "pets/photos/abc.jpg"
    (call,) = fake_sdk["upload"]
    assert call["data"] == b"jpeg-bytes"
    assert call["public_id"] == "pets/photos/abc.jpg"
    assert call["resource_type"] == "image"
    assert call["type"] == "private"
    assert call["overwrite"] is True


def test_save_raw_resource_type_for_non_image(settings, fake_sdk):
    settings.CLOUDINARY_URL = "cloudinary://k:s@c"
    store = CloudinaryStorage()
    store.save("data/notes.txt", ContentFile(b"hi", name="notes.txt"))
    assert fake_sdk["upload"][0]["resource_type"] == "raw"


def test_url_signs_and_expires(settings, fake_sdk):
    settings.CLOUDINARY_URL = "cloudinary://k:s@c"
    store = CloudinaryStorage()
    before = int(time.time())
    url = store.url("flyers/1/flyer.pdf", expire=3600)
    after = int(time.time())
    assert url.startswith("https://res.cloudinary.com/demo/signed/")
    (call,) = fake_sdk["url"]
    assert call["public_id"] == "flyers/1/flyer.pdf"
    assert call["sign_url"] is True
    assert call["type"] == "private"
    assert call["resource_type"] == "image"
    assert call["format"] == "pdf"
    assert before + 3600 <= call["expires_at"] <= after + 3600


def test_url_without_expire_has_no_expires_at(settings, fake_sdk):
    settings.CLOUDINARY_URL = "cloudinary://k:s@c"
    CloudinaryStorage().url("a.jpg")
    assert "expires_at" not in fake_sdk["url"][0]


def test_url_requires_name(settings, fake_sdk):
    settings.CLOUDINARY_URL = "cloudinary://k:s@c"
    with pytest.raises(ValueError, match="storage name"):
        CloudinaryStorage().url(None)


def test_url_handles_bare_string_return(settings, fake_sdk, monkeypatch):
    """Older SDK versions return a plain string instead of (url, options)."""
    settings.CLOUDINARY_URL = "cloudinary://k:s@c"
    monkeypatch.setattr(
        cloudinary.utils, "cloudinary_url", lambda public_id, **kw: f"https://plain/{public_id}"
    )
    assert CloudinaryStorage().url("a.jpg") == "https://plain/a.jpg"


def test_exists_and_size_and_delete(settings, fake_sdk):
    settings.CLOUDINARY_URL = "cloudinary://k:s@c"
    store = CloudinaryStorage()
    assert store.exists("existing.jpg") is True
    assert store.exists("missing.jpg") is False
    assert store.size("existing.jpg") == 1234
    store.delete("pets/photos/abc.jpg")
    assert fake_sdk["destroy"][0]["public_id"] == "pets/photos/abc.jpg"
    assert fake_sdk["destroy"][0]["type"] == "private"


def test_open_fetches_signed_url(settings, fake_sdk, monkeypatch):
    settings.CLOUDINARY_URL = "cloudinary://k:s@c"
    seen: dict = {}

    def fake_get(url, timeout):
        seen["url"] = url
        return httpx.Response(200, content=b"img-bytes", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    store = CloudinaryStorage()
    fh = store.open("pets/photos/abc.jpg", "rb")
    assert fh.read() == b"img-bytes"
    assert seen["url"].endswith("pets/photos/abc.jpg")


def test_storage_helpers_delegate_to_cloudinary(settings, fake_sdk, monkeypatch):
    """upload_bytes/read_bytes/signed_url work against the Cloudinary backend."""
    settings.CLOUDINARY_URL = "cloudinary://k:s@c"
    store = CloudinaryStorage()
    monkeypatch.setattr(storage_helpers, "get_storage", lambda: store)

    key = storage_helpers.upload_bytes("flyers/1/flyer.png", b"png", content_type="image/png")
    assert key == "flyers/1/flyer.png"
    assert fake_sdk["upload"][0]["public_id"] == key

    def fake_get(url, timeout):
        return httpx.Response(200, content=b"png", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    assert storage_helpers.read_bytes(key) == b"png"

    signed = storage_helpers.signed_url(key, expires=120)
    assert signed.startswith("https://res.cloudinary.com/demo/signed/")
    assert fake_sdk["url"][-1]["expires_at"] >= int(time.time()) + 119
