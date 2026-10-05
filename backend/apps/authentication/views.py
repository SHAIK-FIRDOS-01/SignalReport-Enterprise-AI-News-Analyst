"""
Authentication Views for SignalReport.
Replaces: backend/app/api/v1/auth_register.py, backend/app/api/v1/auth_login.py
Ponytail: Standard DRF APIView implementations with SimpleJWT token generation.
Security-audit: Rate-limited verification & login, HttpOnly cookies, timing-safe OTP verification.
"""

import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .serializers import (
    RegisterSerializer,
    VerifyCodeSerializer,
    LoginSerializer,
    RefreshTokenSerializer,
)
from core.security import login_rate_limiter, resolve_client_ip

User = get_user_model()


class RegisterView(APIView):
    """
    Registers a new user directly without email OTP verification.
    Endpoint: POST /api/v1/auth/register/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = User.objects.create_user(
            email=email,
            password=password,
            is_verified=True,
        )

        return Response(
            {
                "status": "success",
                "message": "User registered successfully.",
                "email": email,
                "is_verified": True,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyCodeView(APIView):
    """
    Validates a submitted 6-digit OTP code against the user record and activates the account.
    Endpoints: POST /api/v1/auth/verify-code/, POST /api/v1/auth/verify-otp/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        if login_rate_limiter.is_blocked(email):
            return Response(
                {"detail": "Too many failed verification attempts. Please wait before trying again."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"detail": "Invalid email or verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.verification_code or not secrets.compare_digest(user.verification_code, code):
            login_rate_limiter.record_failure(email)
            if login_rate_limiter.is_blocked(email):
                user.verification_code = None
                user.verification_code_expires_at = None
                user.save(update_fields=["verification_code", "verification_code_expires_at"])
                return Response(
                    {"detail": "Too many failed verification attempts. Verification code has been invalidated."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            return Response(
                {"detail": "Invalid verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.verification_code_expires_at and timezone.now() > user.verification_code_expires_at:
            return Response(
                {"detail": "Verification code has expired. Please request a new code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        login_rate_limiter.reset(email)
        user.is_verified = True
        user.verification_code = None
        user.verification_code_expires_at = None
        user.save(update_fields=["is_verified", "verification_code", "verification_code_expires_at"])

        return Response(
            {
                "status": "success",
                "message": "Account verified successfully.",
            },
            status=status.HTTP_200_OK,
        )


class LoginView(APIView):
    """
    Authenticates credentials, enforces verification, and issues JWT tokens + HttpOnly cookies.
    Endpoint: POST /api/v1/auth/login/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": serializer.errors.get("detail", "Invalid email or password.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = serializer.validated_data["user"]
        if not user.is_verified:
            return Response(
                {"detail": "Email is not verified. Please verify your account before logging in."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response(
            {
                "status": "success",
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                },
            },
            status=status.HTTP_200_OK,
        )

        # Set hardened HttpOnly cookies
        cookie_secure = getattr(settings, "COOKIE_SECURE", False)
        cookie_samesite = getattr(settings, "COOKIE_SAMESITE", "Lax")
        access_expiry = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        refresh_expiry = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())

        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=access_expiry,
            httponly=True,
            samesite=cookie_samesite,
            secure=cookie_secure,
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=refresh_expiry,
            httponly=True,
            samesite=cookie_samesite,
            secure=cookie_secure,
            path="/",
        )

        return response


class RefreshTokenView(APIView):
    """
    Refreshes access tokens via Refresh Token Rotation (RTR).
    Accepts token from JSON body or HttpOnly cookie.
    Endpoint: POST /api/v1/auth/refresh/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        candidate_token = request.data.get("refresh_token") or request.COOKIES.get("refresh_token")
        if not candidate_token:
            return Response(
                {"detail": "Refresh token missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(candidate_token)
            data = {"access": str(refresh.access_token)}

            # Rotate refresh token if rotation enabled
            if getattr(settings, "SIMPLE_JWT", {}).get("ROTATE_REFRESH_TOKENS", True):
                refresh.set_jti()
                refresh.set_exp()
                new_refresh = str(refresh)
            else:
                new_refresh = candidate_token

            response = Response(
                {
                    "status": "success",
                    "access_token": data["access"],
                    "token_type": "bearer",
                },
                status=status.HTTP_200_OK,
            )

            cookie_secure = getattr(settings, "COOKIE_SECURE", False)
            cookie_samesite = getattr(settings, "COOKIE_SAMESITE", "Lax")
            access_expiry = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
            refresh_expiry = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())

            response.set_cookie(
                key="access_token",
                value=data["access"],
                max_age=access_expiry,
                httponly=True,
                samesite=cookie_samesite,
                secure=cookie_secure,
                path="/",
            )
            response.set_cookie(
                key="refresh_token",
                value=new_refresh,
                max_age=refresh_expiry,
                httponly=True,
                samesite=cookie_samesite,
                secure=cookie_secure,
                path="/",
            )

            return response
        except (TokenError, InvalidToken):
            response = Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            response.delete_cookie("access_token", path="/")
            response.delete_cookie("refresh_token", path="/")
            return response


class LogoutView(APIView):
    """
    Revokes authentication cookies and clears session.
    Endpoint: POST /api/v1/auth/logout/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response(
            {
                "status": "success",
                "message": "Successfully logged out.",
            },
            status=status.HTTP_200_OK,
        )
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/")
        return response


class MeView(APIView):
    """
    Returns profile information for the authenticated user.
    Endpoint: GET /api/v1/auth/me/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "id": request.user.id,
                "email": request.user.email,
                "is_verified": request.user.is_verified,
            },
            status=status.HTTP_200_OK,
        )
