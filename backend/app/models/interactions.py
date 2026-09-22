from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint, func

from app.core.database import Base


def get_utc_now() -> datetime:
    """Returns current UTC timestamp with timezone awareness."""
    return datetime.now(timezone.utc)


class Bookmark(Base):
    """
    Tracks articles bookmarked/saved by authenticated users.
    Enforces cascade deletes and composite uniqueness across (user_id, article_id).
    """
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id = Column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_user_article_bookmark"),
    )

    def __repr__(self) -> str:
        return f"<Bookmark(id={self.id}, user_id={self.user_id}, article_id={self.article_id})>"


class ArticleRead(Base):
    """
    Tracks read/unread state of articles per user.
    Enforces cascade deletes and composite uniqueness across (user_id, article_id).
    """
    __tablename__ = "article_reads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id = Column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    read_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_user_article_read"),
    )

    def __repr__(self) -> str:
        return f"<ArticleRead(id={self.id}, user_id={self.user_id}, article_id={self.article_id})>"
