import os
import sys
from pathlib import Path
import pytest
import datetime
import jwt

# Set up paths
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"

for p in [str(root_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from django.conf import settings
from django.test import RequestFactory
from django.http import HttpResponse, JsonResponse
from apps.accounts.models import CustomUser
from apps.accounts.utils import (
    generate_jwt,
    decode_jwt,
    set_jwt_cookie,
    clear_jwt_cookie,
    JWT_COOKIE_NAME,
)
from apps.accounts.middleware import JWTCookieAuthenticationMiddleware


def test_argon2id_password_hashing():
    """Verify that password hashing utilizes Argon2id by default (OWASP Top 1)."""
    assert settings.PASSWORD_HASHERS[0] == 'django.contrib.auth.hashers.Argon2PasswordHasher'
    
    user = CustomUser(email="argon2_test@signalreport.ai")
    raw_password = "SuperSecurePassword#2026!"
    user.set_password(raw_password)
    
    assert user.password.startswith("argon2"), f"Password hash must start with 'argon2', got: {user.password[:15]}"
    assert user.check_password(raw_password) is True
    assert user.check_password("WrongPassword") is False


def test_jwt_generation_and_decoding():
    """Verify JWT encodes claims and can be cryptographically verified."""
    user = CustomUser(id=999, email="jwt_user@signalreport.ai", role="ANALYST")
    token = generate_jwt(user)
    assert isinstance(token, str)
    assert len(token) > 20
    
    payload = decode_jwt(token)
    assert payload is not None
    assert payload["user_id"] == 999
    assert payload["email"] == "jwt_user@signalreport.ai"
    assert payload["role"] == "ANALYST"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_decode_tampered_or_invalid():
    """Verify decode_jwt returns None when token is tampered or expired."""
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tampered.signature"
    assert decode_jwt(invalid_token) is None
    
    # Test expired token
    expired_payload = {
        'user_id': 1,
        'email': 'expired@signalreport.ai',
        'role': 'STANDARD',
        'exp': datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1),
        'iat': datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2),
    }
    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    expired_token = jwt.encode(expired_payload, secret, algorithm='HS256')
    assert decode_jwt(expired_token) is None


def test_set_and_clear_jwt_cookie():
    """Verify set_jwt_cookie configures HttpOnly, SameSite, and max_age correctly."""
    response = HttpResponse("OK")
    sample_token = "sample.jwt.token"
    
    response = set_jwt_cookie(response, sample_token)
    assert JWT_COOKIE_NAME in response.cookies
    cookie = response.cookies[JWT_COOKIE_NAME]
    
    assert cookie.value == sample_token
    assert cookie['httponly'] is True
    assert cookie['samesite'].lower() in ('lax', 'strict')
    
    # Clear cookie
    response = clear_jwt_cookie(response)
    cleared_cookie = response.cookies[JWT_COOKIE_NAME]
    assert cleared_cookie['max-age'] == 0 or cleared_cookie.value == ''


def test_jwt_cookie_authentication_middleware():
    """Verify middleware extracts HttpOnly JWT cookie and attaches authenticated user."""
    rf = RequestFactory()
    user = CustomUser(id=101, email="cookie_auth@signalreport.ai", role="STANDARD")
    token = generate_jwt(user)
    
    # Mock user retrieval in middleware
    middleware = JWTCookieAuthenticationMiddleware(lambda req: HttpResponse(f"User: {req.user.email}"))
    
    # 1. Request with valid cookie
    request = rf.get("/api/me/")
    request.COOKIES[JWT_COOKIE_NAME] = token
    
    # Pre-populate get for user lookup mock if database not loaded
    with pytest.MonkeyPatch.context() as m:
        m.setattr(CustomUser.objects, "filter", lambda **kw: [user] if kw.get("id") == 101 else [])
        response = middleware(request)
        assert request.user.is_authenticated
        assert request.user.email == "cookie_auth@signalreport.ai"
