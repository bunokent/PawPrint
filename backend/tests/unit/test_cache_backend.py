"""Unit tests for the fallback cache backend (Redis with LocMemCache fallback)."""

from unittest.mock import patch

from django.core.cache.backends.redis import RedisCache

from apps.common.cache_backend import FallbackCache


def test_get_returns_default_when_redis_down_and_key_absent():
    cache = FallbackCache("redis://127.0.0.1:1/0", {})
    with patch.object(RedisCache, "get", side_effect=ConnectionError("redis down")):
        assert cache.get("missing", default="default") == "default"


def test_set_get_use_fallback_when_redis_down():
    cache = FallbackCache("redis://127.0.0.1:1/0", {})
    with patch.object(RedisCache, "get", side_effect=ConnectionError("redis down")), \
         patch.object(RedisCache, "set", side_effect=ConnectionError("redis down")):
        assert cache.set("k", "v") is None
        assert cache.get("k", default="default") == "v"
    # the fallback locmem holds the value written during the outage
    assert cache._fallback.get("k") == "v"


def test_delete_incr_fallback_when_redis_down():
    cache = FallbackCache("redis://127.0.0.1:1/0", {})
    cache._fallback.set("k", 5)
    with patch.object(RedisCache, "incr", side_effect=ConnectionError("redis down")):
        assert cache.incr("k") == 6
    with patch.object(RedisCache, "delete", side_effect=ConnectionError("redis down")):
        assert cache.delete("k") is True
    assert cache._fallback.get("k") is None


def test_uses_redis_when_available():
    cache = FallbackCache("redis://127.0.0.1:1/0", {})
    with patch.object(RedisCache, "get", return_value="from-redis"):
        assert cache.get("k") == "from-redis"
