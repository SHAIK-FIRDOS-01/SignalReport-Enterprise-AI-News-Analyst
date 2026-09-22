import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.core.security.email_filter import (
    validate_and_normalize_email,
    InvalidEmailError,
    DisposableEmailError,
)
from app.core.security.crypto import hash_password
from app.services.email_service import send_verification_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: str
    password: str


class VerifyCodeRequest(BaseModel):
    email: str
    code: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Registers a new unverified user account and dispatches a 6-digit OTP code in background.
    """
    try:
        normalized_email = validate_and_normalize_email(request.email)
    except (InvalidEmailError, DisposableEmailError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )

    existing_user = db.query(User).filter_by(email=normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    # Generate cryptographically secure 6-digit numeric OTP
    otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    hashed_pw = hash_password(request.password)

    user = User(
        email=normalized_email,
        hashed_password=hashed_pw,
        is_verified=False,
        verification_code=otp_code,
        verification_code_expires_at=expires_at,
    )
    db.add(user)
    db.commit()

    # Dispatch verification email asynchronously in background
    background_tasks.add_task(send_verification_email, email=normalized_email, code=otp_code)

    return {
        "status": "success",
        "message": "Verification code dispatched to email.",
        "email": normalized_email,
    }


@router.post("/verify-otp", status_code=status.HTTP_200_OK)
@router.post("/verify-code", status_code=status.HTTP_200_OK)
def verify_code(
    request: VerifyCodeRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Validates a submitted 6-digit OTP code against the pending user record and activates the account.
    """
    try:
        normalized_email = validate_and_normalize_email(request.email)
    except Exception:
        normalized_email = request.email.strip().lower()

    user = db.query(User).filter_by(email=normalized_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or verification code.",
        )

    if not user.verification_code or not secrets.compare_digest(user.verification_code, request.code.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )

    if user.verification_code_expires_at is not None:
        expiry = user.verification_code_expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expiry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired. Please request a new code.",
            )

    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires_at = None
    db.commit()

    return {
        "status": "success",
        "message": "Account verified successfully.",
    }
