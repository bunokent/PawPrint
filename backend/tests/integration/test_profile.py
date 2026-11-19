"""Integration: profile update (PATCH /api/auth/profile) + avatar upload (POST /api/auth/avatar)."""

import io

import pytest
from PIL import Image

from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def _png_bytes(color=(30, 120, 200), size=(64, 64)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_patch_profile_updates_display_name_and_phone(auth_client):
    resp = auth_client.patch(
        "/api/auth/profile", {"display_name": "Mia Cruz", "phone": "09171234567"}, format="json"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Mia Cruz"
    assert body["phone"] == "09171234567"
    assert body["avatar_url"] == ""  # no avatar yet
    me = auth_client.get("/api/auth/me").json()
    assert me["display_name"] == "Mia Cruz"


def test_patch_profile_partial_keeps_other_fields(auth_client, user):
    user.display_name = "Original"
    user.save()
    resp = auth_client.patch("/api/auth/profile", {"phone": "09170000000"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["phone"] == "09170000000"
    assert resp.json()["display_name"] == "Original"


def test_patch_profile_empty_body_is_a_noop(auth_client, user):
    user.display_name = "Keep Me"
    user.save()
    resp = auth_client.patch("/api/auth/profile", {}, format="json")
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Keep Me"


def test_patch_profile_guest_401(api_client):
    resp = api_client.patch("/api/auth/profile", {"display_name": "X"}, format="json")
    assert resp.status_code == 401
    assert resp.json()["error"]["session_expired"] is True


def test_patch_profile_too_long_400(auth_client):
    resp = auth_client.patch("/api/auth/profile", {"display_name": "x" * 121}, format="json")
    assert resp.status_code == 400
    assert "display_name" in resp.json()["error"]["fields"]


def test_post_avatar_guest_401(api_client):
    resp = api_client.post("/api/auth/avatar", {"avatar": io.BytesIO(_png_bytes())}, format="multipart")
    assert resp.status_code == 401


def test_post_avatar_missing_file_400(auth_client):
    resp = auth_client.post("/api/auth/avatar", {}, format="multipart")
    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == "Field 'avatar' is required."


def test_post_avatar_non_image_400(auth_client):
    resp = auth_client.post(
        "/api/auth/avatar",
        {"avatar": io.BytesIO(b"not an image at all"), "name": "fake.png"},
        format="multipart",
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "validation_error"
    assert "not a readable image" in resp.json()["error"]["message"]


def test_post_avatar_oversize_400(auth_client):
    from apps.users.services import MAX_AVATAR_BYTES

    resp = auth_client.post(
        "/api/auth/avatar",
        {"avatar": io.BytesIO(b"x" * (MAX_AVATAR_BYTES + 1)), "name": "big.jpg"},
        format="multipart",
    )
    assert resp.status_code == 400
    assert "5 MB" in resp.json()["error"]["message"]


def test_post_avatar_success_stores_and_returns_signed_url(auth_client, user):
    from django.core.files.storage import default_storage

    resp = auth_client.post(
        "/api/auth/avatar",
        {"avatar": io.BytesIO(_png_bytes()), "name": "me.png"},
        format="multipart",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["avatar_path"].startswith(f"avatars/{user.pk}/")
    assert body["avatar_path"].endswith(".jpg")
    assert body["avatar_url"]  # signed URL for the private object
    assert default_storage.exists(body["avatar_path"])
    # EXIF-stripped, re-encoded JPEG (PNG input becomes JPEG)
    with default_storage.open(body["avatar_path"], "rb") as fh:
        assert Image.open(fh).format == "JPEG"
    # /api/auth/me now serves the avatar_url too
    me = auth_client.get("/api/auth/me").json()
    assert me["avatar_url"]


def test_post_avatar_replaces_and_deletes_old_object(auth_client, user):
    from django.core.files.storage import default_storage

    first = auth_client.post(
        "/api/auth/avatar", {"avatar": io.BytesIO(_png_bytes((200, 30, 30))), "name": "a.png"}, format="multipart"
    ).json()
    second = auth_client.post(
        "/api/auth/avatar", {"avatar": io.BytesIO(_png_bytes((30, 200, 30))), "name": "b.png"}, format="multipart"
    ).json()
    assert second["avatar_path"] != first["avatar_path"]
    assert not default_storage.exists(first["avatar_path"])
    assert default_storage.exists(second["avatar_path"])
    user.refresh_from_db()
    assert user.avatar_path == second["avatar_path"]


def test_post_avatar_old_delete_failure_still_succeeds(auth_client, monkeypatch):
    from django.core.files.storage import default_storage

    auth_client.post(
        "/api/auth/avatar", {"avatar": io.BytesIO(_png_bytes()), "name": "a.png"}, format="multipart"
    )

    def boom(key):
        raise OSError("storage gone")

    monkeypatch.setattr(default_storage, "delete", boom)
    resp = auth_client.post(
        "/api/auth/avatar", {"avatar": io.BytesIO(_png_bytes()), "name": "b.png"}, format="multipart"
    )
    assert resp.status_code == 200
    assert resp.json()["avatar_path"].endswith(".jpg")


def test_avatar_url_empty_when_signing_fails(auth_client, user, monkeypatch):
    user.avatar_path = "avatars/x/y.jpg"
    user.save()
    monkeypatch.setattr(
        "apps.common.storage.signed_url", lambda key, expires=3600: (_ for _ in ()).throw(RuntimeError("no url"))
    )
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] == ""


def test_update_profile_service_directly(user):
    from apps.users.services import AuthService

    updated = AuthService.update_profile(user, display_name="  Direct  ", phone=" 123 ")
    assert updated.display_name == "Direct"
    assert updated.phone == "123"
    user.refresh_from_db()
    assert user.display_name == "Direct"


def test_update_avatar_service_rejects_bad_bytes(user):
    import pytest as _pytest

    from apps.users.services import AuthService, ProfileError

    with _pytest.raises(ProfileError):
        AuthService.update_avatar(user, "x.png", b"garbage")
    assert UserFactory  # keep factory import used
