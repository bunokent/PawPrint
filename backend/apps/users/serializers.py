"""Auth serializers."""

from __future__ import annotations

from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = [
            "id", "email", "display_name", "phone", "avatar_path",
            "google_id", "email_verified",
        ]
        read_only_fields = ["id", "email_verified", "google_id"]


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
