import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Request, Cookie, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.models.token import RefreshToken
from app.core.security.crypto import (
    verify_password,
    create_access_token,
    hash_token,
)
from app.core.security.email_filter import validate_and_normalize_email
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Authenticates user credentials, enforces email verification, and issues
    short-lived access tokens and rotating refresh tokens via HttpOnly cookies.
    """
    try:
        normalized_email = validate_and_normalize_email(request.email)
    except Exception:
        normalized_email = request.email.strip().lower()

    user = db.query(User).filter_by(email=normalized_email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email is not verified. Please verify your account before logging in.",
        )

    settings = get_settings()

    # Generate JWT access token
    access_token = create_access_token(
        subject=str(user.id),
        custom_claims={"email": user.email},
    )

    # Generate cryptographically secure refresh token & family record
    raw_refresh = secrets.token_urlsafe(64)
    token_jti = uuid.uuid4()
    refresh_hash = hash_token(raw_refresh)
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    token_record = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        jti=token_jti,
        expires_at=refresh_expires_at,
    )
    db.add(token_record)
    db.commit()

    # Set hardened HttpOnly, Secure, SameSite=Lax cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/refresh", status_code=status.HTTP_200_OK)
def refresh_token_endpoint(
    response: Response,
    request_body: Optional[RefreshRequest] = None,
    refresh_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Executes Refresh Token Rotation (RTR) and detects Token Reuse Attacks.
    If an already revoked refresh token is presented, revokes the user's entire token family.
    """
    token_candidate = refresh_token
    if not token_candidate and request_body and request_body.refresh_token:
        token_candidate = request_body.refresh_token

    if not token_candidate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing.",
        )

    incoming_hash = hash_token(token_candidate)
    token_record = db.query(RefreshToken).filter_by(token_hash=incoming_hash).first()

    # Detect Token Reuse Attack: A revoked token is presented again
    if token_record is not None and token_record.revoked:
        # Invalidate entire token family for user
        db.query(RefreshToken).filter_by(user_id=token_record.user_id).update({"revoked": True})
        user = db.query(User).filter_by(id=token_record.user_id).first()
        if user:
            user.tokens_valid_after = datetime.now(timezone.utc)
        db.commit()

        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token. Token family revoked due to reuse detection.",
        )

    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    # Validate expiration
    token_expiry = token_record.expires_at
    if token_expiry.tzinfo is None:
        token_expiry = token_expiry.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > token_expiry:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired.",
        )

    user = db.query(User).filter_by(id=token_record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    # Check against global revocation timestamp (tokens_valid_after) if available
    token_created_at = getattr(token_record, "created_at", None)
    if token_created_at is not None:
        if token_created_at.tzinfo is None:
            token_created_at = token_created_at.replace(tzinfo=timezone.utc)
        user_valid_after = user.tokens_valid_after
        if user_valid_after.tzinfo is None:
            user_valid_after = user_valid_after.replace(tzinfo=timezone.utc)

        if token_created_at < user_valid_after:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session revoked. Please log in again.",
            )

    # Execute Refresh Token Rotation
    settings = get_settings()
    token_record.revoked = True
    new_jti = uuid.uuid4()
    token_record.replaced_by = new_jti

    new_raw_refresh = secrets.token_urlsafe(64)
    new_hash = hash_token(new_raw_refresh)
    new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_token_record = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        jti=new_jti,
        expires_at=new_expires_at,
    )
    db.add(new_token_record)
    db.commit()

    # Issue new access token
    new_access_token = create_access_token(
        subject=str(user.id),
        custom_claims={"email": user.email},
    )

    # Set rotated cookies
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )

    return {
        "status": "success",
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Revokes the current refresh token and clears authentication cookies.
    """
    if refresh_token:
        incoming_hash = hash_token(refresh_token)
        token_record = db.query(RefreshToken).filter_by(token_hash=incoming_hash).first()
        if token_record:
            token_record.revoked = True
            db.commit()

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")

    return {
        "status": "success",
        "message": "Successfully logged out.",
    }


@router.get("/me", status_code=status.HTTP_200_OK)
def get_me(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns the profile of the currently authenticated user protected by get_current_user route guard.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_verified": current_user.is_verified,
    }

