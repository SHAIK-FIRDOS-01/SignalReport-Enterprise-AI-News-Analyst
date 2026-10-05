"""
Django settings for SignalReport Enterprise AI News Analyst project.
Modular Django 5.x architecture conforming to Enterprise-Contract-Policy.
Satisfies /ponytail (YAGNI, stdlib parsing, zero speculative scaffolding) and /security-audit.
"""

import os
import json
from pathlib import Path
from datetime import timedelta
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment from project root .env and backend/.env
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")

# Security settings
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "signalreport_enterprise_super_secure_jwt_secret_key_32bytes_min"
)
JWT_SECRET_KEY = SECRET_KEY

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = ["*"] if DEBUG else ["localhost", "127.0.0.1", "0.0.0.0"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # Local modular apps
    "apps.authentication.apps.AuthenticationConfig",
    "apps.feed.apps.FeedConfig",
    "apps.ingestion.apps.IngestionConfig",
    "apps.intelligence.apps.IntelligenceConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "core.security.CloudflareProxyMiddleware",
    "core.security.SecurityHeadersMiddleware",
    "core.security.LoginRateLimitMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# Custom Auth User Model
AUTH_USER_MODEL = "authentication.User"

# Database Configuration
# Ponytail: stdlib urlparse parses DATABASE_URL without extra external libraries.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/signalreport"
)

def parse_database_url(url: str):
    # Normalize SQLAlchemy async prefixes
    cleaned_url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    cleaned_url = cleaned_url.replace("sqlite+aiosqlite://", "sqlite://", 1)

    if cleaned_url.startswith("sqlite"):
        db_path = cleaned_url.replace("sqlite:///", "").replace("sqlite://", "") or ":memory:"
        if db_path != ":memory:" and not os.path.isabs(db_path):
            db_path = str(BASE_DIR / db_path)
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": db_path,
        }

    parsed = urlparse(cleaned_url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "localhost",
        "PORT": parsed.port or 5432,
        "CONN_MAX_AGE": 600,
    }

DATABASES = {
    "default": parse_database_url(DATABASE_URL)
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.authentication.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.feed.pagination.StandardFeedPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "200/minute",
    },
    "EXCEPTION_HANDLER": "core.settings.custom_exception_handler",
}

def custom_exception_handler(exc, context):
    """
    Standard exception handler returning uniform JSON error responses
    and preventing internal stack trace leakage.
    """
    from rest_framework.views import exception_handler
    from rest_framework.response import Response
    from rest_framework import status
    import logging

    response = exception_handler(exc, context)

    if response is None:
        logging.getLogger("core.exception").error(
            f"Unhandled server error: {exc}", exc_info=True
        )
        return Response(
            {"detail": "Internal server error occurred. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Normalize detail shape if response data is dict with detail or errors
    if isinstance(response.data, dict) and "detail" not in response.data:
        # If serializer errors (e.g. {'email': ['This field is required.']})
        first_key = next(iter(response.data))
        first_val = response.data[first_key]
        msg = first_val[0] if isinstance(first_val, list) and first_val else str(first_val)
        response.data["detail"] = f"{first_key}: {msg}" if first_key != "non_field_errors" else msg

    return response

# SimpleJWT configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "SIGNING_KEY": JWT_SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "sub",
}

# CORS Configuration
# Whitelisting local Vite dev server and configured origins
raw_cors = os.getenv("CORS_ORIGINS", "")
default_cors = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

if raw_cors:
    try:
        parsed_cors = json.loads(raw_cors) if raw_cors.startswith("[") else [o.strip() for o in raw_cors.split(",")]
        CORS_ALLOWED_ORIGINS = list(set(default_cors + [o.strip() for o in parsed_cors if o.strip()]))
    except Exception:
        CORS_ALLOWED_ORIGINS = default_cors
else:
    CORS_ALLOWED_ORIGINS = default_cors

CORS_ALLOW_CREDENTIALS = True

# Cookie Security Flags
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "False").lower() in ("true", "1", "yes")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")

# Ingestion & External APIs
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")
GNEWS_BASE_URL = os.getenv("GNEWS_BASE_URL", "https://gnews.io/api/v4")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# LLM Rate Limiting & Cooldown Ban
LLM_MAX_REQUESTS_BEFORE_BAN = int(os.getenv("LLM_MAX_REQUESTS_BEFORE_BAN", "3"))
LLM_BAN_DURATION_HOURS = int(os.getenv("LLM_BAN_DURATION_HOURS", "4"))

# GNews Ingestion Budget & Quota Management
GNEWS_MAX_DAILY_CALLS = int(os.getenv("GNEWS_MAX_DAILY_CALLS", "80"))
GNEWS_CATEGORY_COOLDOWN_MINUTES = int(os.getenv("GNEWS_CATEGORY_COOLDOWN_MINUTES", "90"))

