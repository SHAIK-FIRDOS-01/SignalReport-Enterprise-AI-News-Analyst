import secrets
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Union, Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.article import Article

logger = logging.getLogger("article_repository")


def normalize_article_data(
    item: Dict[str, Any],
    default_category: str = "general",
    country: str = "in",
    language: str = "en",
) -> Optional[Dict[str, Any]]:
    """
    Normalizes raw article dictionaries (e.g. from GNews JSON responses) into
    a schema-compliant mapping for database persistence.
    Generates a cryptographically secure URL-safe share_token via secrets.token_urlsafe(8).
    """
    title = item.get("title")
    url = item.get("url")
    if not title or not url:
        return None

    # Resolve published_at timestamp
    raw_pub = item.get("published_at") or item.get("publishedAt")
    if isinstance(raw_pub, datetime):
        pub_dt = raw_pub
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
    elif isinstance(raw_pub, str):
        try:
            cleaned_str = raw_pub.replace("Z", "+00:00")
            pub_dt = datetime.fromisoformat(cleaned_str)
        except Exception:
            pub_dt = datetime.now(timezone.utc)
    else:
        pub_dt = datetime.now(timezone.utc)

    # Resolve source name
    source_val = item.get("source_name")
    if not source_val:
        src = item.get("source")
        if isinstance(src, dict):
            source_val = src.get("name", "Unknown")
        elif isinstance(src, str):
            source_val = src
        else:
            source_val = "Unknown"

    # Generate cryptographically secure URL-safe share_token (8 bytes = 11 base64 chars)
    share_token = item.get("share_token") or secrets.token_urlsafe(8)

    return {
        "title": str(title)[:500],
        "description": item.get("description"),
        "content": item.get("content"),
        "url": str(url)[:1000],
        "image_url": item.get("image_url") or item.get("image"),
        "source_name": str(source_val)[:100],
        "category": str(item.get("category") or default_category)[:50],
        "country": str(item.get("country") or country)[:10],
        "language": str(item.get("language") or language)[:10],
        "share_token": str(share_token)[:16],
        "published_at": pub_dt,
    }


class ArticleRepository:
    """
    Data repository handling atomic and idempotent batch operations for news articles.
    """

    @staticmethod
    def _prepare_insert_stmt(dialect_name: str, records: List[Dict[str, Any]]):
        """
        Builds dialect-specific INSERT ... ON CONFLICT (url) DO NOTHING statement.
        """
        if dialect_name == "postgresql":
            stmt = pg_insert(Article).values(records)
        else:
            stmt = sqlite_insert(Article).values(records)
        return stmt.on_conflict_do_nothing(index_elements=["url"])

    @classmethod
    def _deduplicate_batch(cls, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates records within the incoming batch by URL to avoid multi-row
        intra-statement conflicts.
        """
        unique_map = {}
        for r in records:
            if r["url"] not in unique_map:
                unique_map[r["url"]] = r
        return list(unique_map.values())

    @classmethod
    async def batch_insert_async(
        cls,
        session: AsyncSession,
        articles: List[Dict[str, Any]],
        category: str = "general",
    ) -> int:
        """
        Asynchronously persists a batch of articles with atomic ON CONFLICT (url) DO NOTHING.
        Returns the count of candidate articles processed.
        """
        if not articles:
            return 0

        records = [
            norm for a in articles
            if (norm := normalize_article_data(a, default_category=category)) is not None
        ]
        if not records:
            return 0

        clean_batch = cls._deduplicate_batch(records)

        bind = session.bind
        dialect_name = bind.dialect.name if bind else "postgresql"

        stmt = cls._prepare_insert_stmt(dialect_name, clean_batch)
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Asynchronously processed {len(clean_batch)} articles for category '{category}'")
        return len(clean_batch)

    @classmethod
    def batch_insert_sync(
        cls,
        session: Session,
        articles: List[Dict[str, Any]],
        category: str = "general",
    ) -> int:
        """
        Synchronously persists a batch of articles with atomic ON CONFLICT (url) DO NOTHING.
        Returns the count of candidate articles processed.
        """
        if not articles:
            return 0

        records = [
            norm for a in articles
            if (norm := normalize_article_data(a, default_category=category)) is not None
        ]
        if not records:
            return 0

        clean_batch = cls._deduplicate_batch(records)

        bind = session.get_bind()
        dialect_name = bind.dialect.name if bind else "postgresql"

        stmt = cls._prepare_insert_stmt(dialect_name, clean_batch)
        session.execute(stmt)
        session.commit()
        logger.info(f"Synchronously processed {len(clean_batch)} articles for category '{category}'")
        return len(clean_batch)

    @classmethod
    async def batch_insert(
        cls,
        session: Union[AsyncSession, Session],
        articles: List[Dict[str, Any]],
        category: str = "general",
    ) -> int:
        """
        Unified dispatch: routes to async or sync batch insertion based on session type.
        """
        if isinstance(session, AsyncSession):
            return await cls.batch_insert_async(session, articles, category)
        return cls.batch_insert_sync(session, articles, category)
