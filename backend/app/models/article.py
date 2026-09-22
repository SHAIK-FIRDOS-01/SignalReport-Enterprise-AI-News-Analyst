import sqlite3
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Index,
    func,
    Computed,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import TSVECTOR

from app.core.database import Base


@event.listens_for(Engine, "connect")
def _register_sqlite_tsvector(dbapi_connection, connection_record):
    """
    Registers PostgreSQL full-text search mock functions on SQLite database connections
    to allow SQLite in-memory databases (sync and aiosqlite) to compile and run computed search_vector columns.
    """
    if hasattr(dbapi_connection, "create_function"):
        try:
            dbapi_connection.create_function(
                "to_tsvector", 2, lambda cfg, txt: txt or "", deterministic=True
            )
            dbapi_connection.create_function(
                "to_tsvector", 1, lambda txt: txt or "", deterministic=True
            )
        except Exception:
            pass


class TSVectorType(TypeDecorator):
    """
    Cross-dialect TSVECTOR type. Compiles to native PostgreSQL TSVECTOR
    in production and falls back to TEXT on SQLite for unit tests.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())


class Article(Base):
    """
    Article persistence model storing syndicated enterprise news intelligence.
    Includes PostgreSQL GIN-indexed full-text search vector generated automatically
    from the article title and description.
    """
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    url = Column(String(1000), unique=True, index=True, nullable=False)
    image_url = Column(String(1000), nullable=True)
    source_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    country = Column(String(10), nullable=False, default="in")
    language = Column(String(10), nullable=False, default="en")
    share_token = Column(String(16), unique=True, index=True, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Generated full-text search vector computed automatically from title and description
    search_vector = Column(
        TSVectorType,
        Computed(
            "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))",
            persisted=True,
        ),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_articles_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_articles_category_published_at", "category", published_at.desc()),
    )

    def __repr__(self) -> str:
        return f"<Article(id={self.id}, title='{self.title[:30]}...', category='{self.category}')>"
