"""
Unit and Integration Tests for SignalReport Authentication Module.
Replaces: backend/tests/test_auth_*.py, test_login_rotation.py, test_register_flow.py
Ponytail: Standard Django TestCase and DRF APIClient without complex fixtures.
Security-audit: Adversarial tests covering brute-force, expired OTP, invalid credentials, and session revocation.
"""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.security import login_rate_limiter
from .services import sent_verification_emails

User = get_user_model()


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        login_rate_limiter.clear()
        sent_verification_emails.clear()

        self.user_email = "analyst@signalreport.io"
        self.user_password = "SecurePassword123!"
        self.verified_user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password,
            is_verified=True,
        )

    def test_register_success(self):
        url = reverse("api-v1-auth:register")
        payload = {
            "email": "newuser@signalreport.io",
            "password": "StrongPassword123!",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["email"], "newuser@signalreport.io")
        self.assertTrue(response.data["is_verified"])

        created_user = User.objects.filter(email="newuser@signalreport.io").first()
        self.assertIsNotNone(created_user)
        self.assertTrue(created_user.is_verified)

        # Zero emails sent (Email feature removed)
        self.assertEqual(len(sent_verification_emails), 0)


    def test_register_duplicate_email(self):
        url = reverse("api-v1-auth:register")
        payload = {
            "email": self.user_email,
            "password": "AnotherPassword123!",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_disposable_email(self):
        url = reverse("api-v1-auth:register")
        payload = {
            "email": "attacker@tempmail.com",
            "password": "StrongPassword123!",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        url = reverse("api-v1-auth:register")
        payload = {
            "email": "shortpw@signalreport.io",
            "password": "short",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_code_success(self):
        unverified = User.objects.create_user(
            email="pending@signalreport.io",
            password="SecurePassword123!",
            is_verified=False,
            verification_code="654321",
            verification_code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        url = reverse("api-v1-auth:verify-code")
        response = self.client.post(url, {"email": "pending@signalreport.io", "code": "654321"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")

        unverified.refresh_from_db()
        self.assertTrue(unverified.is_verified)
        self.assertIsNone(unverified.verification_code)

    def test_verify_code_expired(self):
        User.objects.create_user(
            email="expired@signalreport.io",
            password="SecurePassword123!",
            is_verified=False,
            verification_code="112233",
            verification_code_expires_at=timezone.now() - timedelta(minutes=1),
        )

        url = reverse("api-v1-auth:verify-code")
        response = self.client.post(url, {"email": "expired@signalreport.io", "code": "112233"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", response.data["detail"].lower())

    def test_verify_code_brute_force_lockout(self):
        User.objects.create_user(
            email="target@signalreport.io",
            password="SecurePassword123!",
            is_verified=False,
            verification_code="998877",
            verification_code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        url = reverse("api-v1-auth:verify-code")
        for _ in range(4):
            resp = self.client.post(url, {"email": "target@signalreport.io", "code": "000000"}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # 5th failed attempt should trigger lockout
        fifth = self.client.post(url, {"email": "target@signalreport.io", "code": "000000"}, format="json")
        self.assertEqual(fifth.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Code invalidated in database
        target = User.objects.get(email="target@signalreport.io")
        self.assertIsNone(target.verification_code)

    def test_login_success(self):
        url = reverse("api-v1-auth:login")
        payload = {
            "email": self.user_email,
            "password": self.user_password,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertIn("access_token", response.data)
        self.assertEqual(response.data["token_type"], "bearer")
        self.assertEqual(response.data["user"]["email"], self.user_email)

        # Check HttpOnly cookies
        self.assertIn("access_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_login_unverified_forbidden(self):
        User.objects.create_user(
            email="unverified@signalreport.io",
            password="SecurePassword123!",
            is_verified=False,
        )
        url = reverse("api-v1-auth:login")
        response = self.client.post(
            url,
            {"email": "unverified@signalreport.io", "password": "SecurePassword123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("not verified", response.data["detail"])

    def test_login_invalid_password(self):
        url = reverse("api-v1-auth:login")
        response = self.client.post(
            url,
            {"email": self.user_email, "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_cookie(self):
        refresh = RefreshToken.for_user(self.verified_user)
        self.client.cookies["refresh_token"] = str(refresh)

        url = reverse("api-v1-auth:refresh")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertIn("access_token", response.data)
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)

    def test_logout(self):
        url = reverse("api-v1-auth:logout")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Cookies should be expired / emptied
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_me_authenticated(self):
        refresh = RefreshToken.for_user(self.verified_user)
        access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        url = reverse("api-v1-auth:me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.verified_user.id)
        self.assertEqual(response.data["email"], self.verified_user.email)
        self.assertTrue(response.data["is_verified"])

    def test_me_unauthenticated(self):
        url = reverse("api-v1-auth:me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
