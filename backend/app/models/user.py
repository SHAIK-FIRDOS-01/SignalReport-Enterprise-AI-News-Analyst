from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base


def get_utc_now() -> datetime:
    """Returns current UTC timestamp with timezone awareness."""
    return datetime.now(timezone.utc)


class User(Base):
    """
    SQLAlchemy 2.0 User persistence model representing identity, credentials,
    verification state, and bulk token revocation checkpoints.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String(6), nullable=True)
    verification_code_expires_at = Column(DateTime(timezone=True), nullable=True)
    tokens_valid_after = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, server_default=func.now(), nullable=False)

    # Token family cascade
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
