"""AuthService — registration, login, logout and Google/Gmail OAuth 2.0.

All writes are transactional. Google sign-in supports one-click Gmail registration,
linking an existing email account, and existing Google sign-in, via django-allauth's
SocialLogin completion machinery.
"""

from __future__ import annotations

import logging

import httpx
from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.http import HttpRequest

from .dto import AuthResult, GoogleProfile
from .models import User
from .selectors import get_user_by_email, get_user_by_google_id

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class AuthError(Exception):
    """Authentication failure with a client-safe message."""


def google_authorize_url(redirect_uri: str) -> str:
    """Build the Google OAuth 2.0 consent URL from the allauth provider settings."""
    provider_cfg: dict = settings.SOCIALACCOUNT_PROVIDERS["google"]
    app = provider_cfg["APP"]
    scope_list: list[str] = list(provider_cfg.get("SCOPE", ["openid", "email", "profile"]))
    scope = " ".join(scope_list)
    from urllib.parse import urlencode

    params = {
        "client_id": str(app["client_id"]),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def _exchange_google_code(code: str, redirect_uri: str) -> GoogleProfile:
    """Exchange an authorization code for tokens and fetch the verified profile."""
    google_cfg: dict = settings.SOCIALACCOUNT_PROVIDERS["google"]
    app: dict = google_cfg["APP"]
    client_id = str(app["client_id"])
    client_secret = str(app["secret"])
    with httpx.Client(timeout=10) as client:
        token_resp = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]
        info_resp = client.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
        info_resp.raise_for_status()
        info = info_resp.json()
    return GoogleProfile(
        sub=str(info["sub"]),
        email=str(info["email"]),
        email_verified=bool(info.get("email_verified", False)),
        name=str(info.get("name", "")),
        picture=str(info.get("picture", "")),
    )


class AuthService:
    """All auth writes/reads orchestration."""

    @staticmethod
    @transaction.atomic
    def register(email: str, password: str, display_name: str = "") -> User:
        email = email.strip().lower()
        if get_user_by_email(email) is not None:
            raise AuthError("An account with this email already exists.")
        user = User.objects.create_user(email=email, password=password, display_name=display_name)
        return user  # type: ignore[return-value]

    @staticmethod
    def login(request: HttpRequest, email: str, password: str) -> User:
        user = authenticate(request, email=email.strip().lower(), password=password)
        if user is None:
            raise AuthError("Invalid email or password.")
        login(request, user)
        return user  # type: ignore[return-value]

    @staticmethod
    def logout(request: HttpRequest) -> None:
        logout(request)

    @staticmethod
    @transaction.atomic
    def google_callback(request: HttpRequest, code: str, redirect_uri: str) -> AuthResult:
        """Complete Google sign-in: Gmail one-click registration, account linking, or sign-in."""
        profile = _exchange_google_code(code, redirect_uri)

        existing = get_user_by_google_id(profile.sub)
        created = False
        if existing is not None:
            user = existing
        else:
            by_email = get_user_by_email(profile.email)
            if by_email is not None:
                # Link the Google identity to the existing email account.
                by_email.google_id = profile.sub
                by_email.email_verified = by_email.email_verified or profile.email_verified
                if not by_email.display_name and profile.name:
                    by_email.display_name = profile.name
                by_email.save(update_fields=["google_id", "email_verified", "display_name"])
                user = by_email
            else:
                # One-click Gmail registration through allauth's SocialLogin.
                user = User.objects.create_user(
                    email=profile.email,
                    password=None,
                    display_name=profile.name,
                    google_id=profile.sub,
                    email_verified=profile.email_verified,
                )
                created = True

        # Record/refresh the allauth SocialAccount so allauth stays the source of truth.
        SocialAccount.objects.update_or_create(
            provider="google",
            uid=profile.sub,
            defaults={
                "user": user,
                "extra_data": {
                    "email": profile.email,
                    "name": profile.name,
                    "picture": profile.picture,
                    "email_verified": profile.email_verified,
                },
            },
        )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return AuthResult(user_id=str(user.pk), created=created)
