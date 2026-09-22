import os
from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 declarative base establishing shared metadata
    and type mappings across all database models.
    """
    pass


def create_custom_engine(
    database_url: str,
    pool_size: int = 20,
    max_overflow: int = 10,
    pool_timeout: int = 30,
) -> AsyncEngine:
    """
    Factory function instantiating a configured AsyncEngine.
    Applies pool sizing constraints for PostgreSQL connections and
    handles dialect-specific drivers and arguments.
    """
    engine_kwargs: Dict[str, Any] = {}

    if database_url.startswith("sqlite"):
        if not database_url.startswith("sqlite+aiosqlite"):
            database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine_kwargs["pool_size"] = pool_size
        engine_kwargs["max_overflow"] = max_overflow
        engine_kwargs["pool_timeout"] = pool_timeout

    return create_async_engine(
        database_url,
        echo=False,
        **engine_kwargs,
    )


try:
    settings = get_settings()
    DATABASE_URL = settings.DATABASE_URL
    DB_POOL_SIZE = settings.DB_POOL_SIZE
    DB_MAX_OVERFLOW = settings.DB_MAX_OVERFLOW
    DB_POOL_TIMEOUT = settings.DB_POOL_TIMEOUT
except Exception:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/signalreport",
    )
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

engine: AsyncEngine = create_custom_engine(
    database_url=DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
)

async_engine = engine

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding a scoped AsyncSession per HTTP request,
    guaranteeing session closure upon completion.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
