"""Cache backend — Redis when available, in-memory fallback otherwise.

Host-side ``python manage.py runserver`` (no compose, Redis not running) keeps
working: throttles and the session cache fall back to ``LocMemCache`` instead of
raising ``ConnectionError``. Inside compose, ``REDIS_URL`` points at the
``redis`` service and Redis is used normally.
"""

from __future__ import annotations

import redis
from django.core.cache.backends.locmem import LocMemCache
from django.core.cache.backends.redis import RedisCache


class FallbackCache(RedisCache):
    """Redis-backed cache that silently falls back to LocMemCache per-operation."""

    def __init__(self, location: str, params: dict) -> None:
        super().__init__(location, params)
        self._fallback = LocMemCache("fallback", params)

    def _redis_call(self, method, *args, **kwargs):
        try:
            return getattr(super(), method)(*args, **kwargs)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, OSError):
            return getattr(self._fallback, method)(*args, **kwargs)

    def get(self, key, default=None, version=None):  # noqa: D401
        return self._redis_call("get", key, default=default, version=version)

    def set(self, key, value, timeout=None, version=None):  # noqa: D401
        return self._redis_call("set", key, value, timeout=timeout, version=version)

    def add(self, key, value, timeout=None, version=None):  # noqa: D401
        return self._redis_call("add", key, value, timeout=timeout, version=version)

    def get_many(self, keys, version=None):  # noqa: D401
        return self._redis_call("get_many", keys, version=version)

    def set_many(self, data, timeout=None, version=None):  # noqa: D401
        return self._redis_call("set_many", data, timeout=timeout, version=version)

    def delete(self, key, version=None):  # noqa: D401
        return self._redis_call("delete", key, version=version)

    def clear(self):  # noqa: D401
        return self._redis_call("clear")

    def incr(self, key, delta=1, version=None):  # noqa: D401
        return self._redis_call("incr", key, delta=delta, version=version)

    def decr(self, key, delta=1, version=None):  # noqa: D401
        return self._redis_call("decr", key, delta=delta, version=version)

    def __contains__(self, key):  # noqa: D401
        return self._redis_call("__contains__", key)

    def ttl(self, key, version=None):  # noqa: D401
        return self._redis_call("ttl", key, version=version)

