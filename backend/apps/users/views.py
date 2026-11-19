"""Thin auth views (≤15 lines each): validate → service → respond."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttles import AuthWriteThrottle, UploadThrottle

from .models import User
from .selectors import get_user_by_id
from .serializers import (
    GoogleCallbackSerializer,
    GoogleUrlSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .services import AuthError, AuthService, ProfileError, google_authorize_url


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthWriteThrottle]
    throttle_scope = "auth_write"

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = AuthService.register(**serializer.validated_data)
        except AuthError as exc:
            return Response({"error": {"code": "auth_error", "message": str(exc)}}, status=400)
        AuthService.login(request, user.email, serializer.validated_data["password"])
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthWriteThrottle]
    throttle_scope = "auth_write"

    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = AuthService.login(request, **serializer.validated_data)
        except AuthError as exc:
            return Response({"error": {"code": "auth_error", "message": str(exc)}}, status=400)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthWriteThrottle]
    throttle_scope = "auth_write"

    def post(self, request: Request) -> Response:
        AuthService.logout(request)
        return Response({"status": "logged_out"})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)
        return Response(UserSerializer(user).data)


class ProfileView(APIView):
    """PATCH /api/auth/profile — update display_name and/or phone."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=ProfileUpdateSerializer, responses={200: UserSerializer})
    def patch(self, request: Request) -> Response:
        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = request.user
        assert isinstance(user, User)
        user = AuthService.update_profile(user, **serializer.validated_data)
        return Response(UserSerializer(user).data)


class AvatarUploadView(APIView):
    """POST /api/auth/avatar — profile picture upload (10/min, no pet gate)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [UploadThrottle]
    throttle_scope = "upload"
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(responses={200: UserSerializer})
    def post(self, request: Request) -> Response:
        upload = request.FILES.get("avatar")
        if upload is None:
            return Response(
                {"error": {"code": "validation_error", "message": "Field 'avatar' is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        assert isinstance(user, User)
        try:
            user = AuthService.update_avatar(user, upload.name or "avatar.jpg", upload.read())
        except ProfileError as exc:
            return Response(
                {"error": {"code": "validation_error", "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(UserSerializer(user).data)


class GoogleUrlView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=GoogleUrlSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        serializer = GoogleUrlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = google_authorize_url(serializer.validated_data["redirect_uri"])
        return Response({"url": url})


class GoogleCallbackView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthWriteThrottle]
    throttle_scope = "auth_write"

    @extend_schema(request=GoogleCallbackSerializer, responses={200: UserSerializer})
    def post(self, request: Request) -> Response:
        serializer = GoogleCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = AuthService.google_callback(request, **serializer.validated_data)
        except AuthError as exc:
            return Response({"error": {"code": "auth_error", "message": str(exc)}}, status=400)
        except Exception:
            return Response(
                {"error": {"code": "oauth_error", "message": "Google sign-in failed."}}, status=400
            )
        import uuid as _uuid

        user = get_user_by_id(_uuid.UUID(result.user_id))
        return Response({"user": UserSerializer(user).data, "created": result.created})
