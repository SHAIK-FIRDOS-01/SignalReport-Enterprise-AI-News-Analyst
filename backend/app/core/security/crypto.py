import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple, Union
import bcrypt
import jwt

from app.core.config import get_settings


class TokenError(Exception):
    """Base exception for all token-related failures."""
    pass


class TokenExpiredError(TokenError):
    """Raised when a token signature has expired."""
    pass


class InvalidTokenError(TokenError):
    """Raised when a token fails signature verification, tampering checks, or algorithm whitelist."""
    pass


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using Bcrypt with a cryptographically secure salt.
    Bcrypt has a 72-byte truncation boundary; input is safely bounded.
    """
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text candidate password against a stored Bcrypt hash in constant time.
    """
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


def hash_token(token: str) -> str:
    """
    Generates a deterministic SHA-256 hex digest of a token string for indexing and storage.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    custom_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generates a signed short-lived JWT access token containing standard claims.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
        "iss": "signalreport-auth",
        "aud": "signalreport-api",
        "type": "access",
    }

    if custom_claims:
        payload.update(custom_claims)

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


def create_refresh_token(
    subject: Union[str, int],
    jti: Optional[uuid.UUID] = None,
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, uuid.UUID]:
    """
    Generates a signed long-lived JWT refresh token with explicit JTI tracking for rotation.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    token_jti = jti or uuid.uuid4()

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(token_jti),
        "iss": "signalreport-auth",
        "aud": "signalreport-api",
        "type": "refresh",
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, token_jti


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies a JWT token against the algorithm whitelist, signature, and expiration.

    Raises:
        TokenExpiredError: If the token has expired.
        InvalidTokenError: If the token signature is invalid, algorithm unwhitelisted, or format tampered.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer="signalreport-auth",
            audience="signalreport-api",
            options={"require": ["sub", "exp", "iat", "jti", "iss", "aud"]},
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(f"Invalid token: {exc}") from exc
