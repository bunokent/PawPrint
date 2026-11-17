"""Scoped rate throttles."""

from rest_framework.throttling import ScopedRateThrottle


class AuthWriteThrottle(ScopedRateThrottle):
    """20/min on auth mutation endpoints."""

    scope = "auth_write"


class UploadThrottle(ScopedRateThrottle):
    """10/min on photo upload endpoints."""

    scope = "upload"
