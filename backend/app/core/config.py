import json
from typing import Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application configuration loaded from environment variables and .env files.
    Enforces cryptographic entropy constraints and encapsulates database, API, security,
    CORS, cookie, polling, and mail transport parameters.
    """

    # Database connection parameters
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/signalreport"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # GNews ingestion credentials
    GNEWS_API_KEY: str = ""
    GNEWS_BASE_URL: str = "https://gnews.io/api/v4"

    # JWT symmetric & asymmetric keys and token lifespan
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_PRIVATE_KEY: Optional[str] = None
    JWT_PUBLIC_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # CORS whitelist (accepts list of strings, JSON array string, or comma-separated string)
    CORS_ORIGINS: Union[list[str], str] = ["http://localhost:3000", "http://localhost:8000"]

    # Cookie security flags
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None
    COOKIE_HTTPONLY: bool = True

    # Background polling intervals
    POLLING_INTERVAL_HOURS: int = 2
    POLLING_INTERVAL_SECONDS: int = 7200

    # SMTP mail transport configuration
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@signalreport.io"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def validate_jwt_secret_key_entropy(cls, value: str) -> str:
        """
        Enforce a minimum entropy requirement of 256 bits (32 bytes) for HMAC-SHA256.
        """
        if not value or len(value.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 256 bits (32 characters)")
        return value

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, value: Union[list[str], str]) -> list[str]:
        """
        Support comma-separated strings or JSON-encoded arrays for CORS_ORIGINS from env.
        """
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed]
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Returns a cached singleton instance of Settings, reading from environment or .env.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
