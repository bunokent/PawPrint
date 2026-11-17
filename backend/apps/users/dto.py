"""Frozen DTOs for the auth service."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoogleProfile:
    sub: str
    email: str
    email_verified: bool
    name: str
    picture: str


@dataclass(frozen=True)
class AuthResult:
    user_id: str
    created: bool
