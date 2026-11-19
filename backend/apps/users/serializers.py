"""Auth serializers."""

from __future__ import annotations

from rest_framework import serializers

from apps.common import storage

from .models import User


class UserSerializer(serializers.ModelSerializer[User]):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "display_name", "phone", "avatar_path", "avatar_url",
            "google_id", "email_verified",
        ]
        read_only_fields = ["id", "email_verified", "google_id"]

    def get_avatar_url(self, obj: User) -> str:
        """Fresh signed URL for the private avatar object ("" when none / on failure)."""
        if not obj.avatar_path:
            return ""
        try:
            return storage.signed_url(obj.avatar_path)
        except Exception:
            return ""


class ProfileUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, max_length=128, write_only=True)
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class GoogleCallbackSerializer(serializers.Serializer):
    code = serializers.CharField()
    redirect_uri = serializers.CharField()


class GoogleUrlSerializer(serializers.Serializer):
    redirect_uri = serializers.CharField()
