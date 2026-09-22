import uuid
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base


class RefreshToken(Base):
    """
    Refresh Token Rotation (RTR) persistence entity.
    Maintains cryptographic token family tracking, revocation status,
    and child successor pointer (replaced_by) for reuse detection.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    jti = Column(Uuid(as_uuid=True), unique=True, index=True, nullable=False, default=uuid.uuid4)
    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    replaced_by = Column(Uuid(as_uuid=True), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")
