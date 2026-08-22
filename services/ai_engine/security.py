import secrets
from fastapi import Header, HTTPException, status
try:
    from .config import settings
except ImportError:
    from config import settings


async def verify_internal_service_key(
    x_internal_service_key: str | None = Header(None, alias="X-Internal-Service-Key")
) -> str:
    """
    Cryptographic verification of X-Internal-Service-Key header.
    Utilizes constant-time string comparison (secrets.compare_digest) to prevent timing attacks.
    """
    if not x_internal_service_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Missing X-Internal-Service-Key header"
        )
    
    expected_key = settings.INTERNAL_SERVICE_KEY
    if not expected_key or not secrets.compare_digest(x_internal_service_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid X-Internal-Service-Key"
        )
    
    return x_internal_service_key
