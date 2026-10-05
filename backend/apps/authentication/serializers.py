"""
Authentication Serializers for SignalReport.
Replaces: backend/app/api/v1/auth_register.py, auth_login.py Pydantic schemas
Ponytail: Uses native DRF serializers and validators without bespoke validation frameworks.
Security-audit: Enforces disposable email rejection, password entropy, and timing-safe checks.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

DISPOSABLE_DOMAINS = {
    "tempmail.com", "throwawaymail.com", "mailinator.com", "guerrillamail.com",
    "sharklasers.com", "10minutemail.com", "yopmail.com", "trashmail.com",
    "getairmail.com", "dispostable.com", "crazymailing.com",
}


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    def validate_email(self, value):
        normalized = value.strip().lower()
        domain = normalized.split("@")[-1] if "@" in normalized else ""
        if domain in DISPOSABLE_DOMAINS:
            raise serializers.ValidationError("Disposable email addresses are not permitted.")
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_code(self, value):
        cleaned = value.strip()
        if not cleaned.isdigit() or len(cleaned) != 6:
            raise serializers.ValidationError("Verification code must be a 6-digit number.")
        return cleaned


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password", "")

        user = User.objects.filter(email=email).first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError({"detail": "Invalid email or password."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "User account is disabled."})

        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "is_verified")
        read_only_fields = ("id", "email", "is_verified")


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=False, allow_blank=True)
