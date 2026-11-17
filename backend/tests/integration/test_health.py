"""Integration: health endpoint."""

import pytest

pytestmark = pytest.mark.django_db


def test_health_ok(api_client):
    response = api_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "pawprint"}


def test_health_no_db_queries(api_client, django_assert_num_queries):
    with django_assert_num_queries(0):
        response = api_client.get("/api/health")
    assert response.status_code == 200


def test_admin_is_not_installed(api_client):
    """django.contrib.admin must be completely removed."""
    response = api_client.get("/admin/")
    assert response.status_code == 404
    from django.apps import apps

    assert not apps.is_installed("django.contrib.admin")
