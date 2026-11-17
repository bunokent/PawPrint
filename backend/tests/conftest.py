"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _fast_password_hasher(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import caches

    caches["default"].clear()
    yield
    caches["default"].clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    from apps.users.factories import UserFactory

    return UserFactory()


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
