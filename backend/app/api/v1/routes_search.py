import logging
import math
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, literal
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.article import Article
from app.models.interactions import Bookmark, ArticleRead
from app.api.deps import get_optional_current_user
from app.services.gnews_client import GNewsClient
from app.services.article_repository import ArticleRepository

logger = logging.getLogger("routes_search")

router = APIRouter(prefix="/news", tags=["Search"])


class ArticleSearchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    source_name: str
    category: str
    country: str
    language: str
    share_token: str
    published_at: datetime
    created_at: datetime
    is_bookmarked: bool = False
    is_read: bool = False


class SearchResponse(BaseModel):
    items: List[ArticleSearchItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    source: str


def _build_search_filter(db: Session, query_str: str):
    """
    Constructs cross-dialect full-text / keyword search filter.
    Uses PostgreSQL TSVECTOR plainto_tsquery when on PostgreSQL,
    and falls back to case-insensitive ILIKE pattern matching on SQLite.
    """
    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind else "postgresql"
    clean_q = query_str.strip()
    pattern = f"%{clean_q}%"

    if dialect_name == "postgresql":
        return or_(
            Article.search_vector.op("@@")(func.plainto_tsquery("english", clean_q)),
            Article.title.ilike(pattern),
            Article.description.ilike(pattern),
        )
    else:
        return or_(
            Article.title.ilike(pattern),
            Article.description.ilike(pattern),
            Article.search_vector.ilike(pattern),
        )


@router.get(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
)
async def search_articles(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Search keywords"),
    category: Optional[str] = Query(None, description="Filter results by category"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """
    Executes hybrid search across articles with mid-flight disconnect detection:
    1. Disconnect Guard (Entry): Aborts immediately if the client cancelled before search execution.
    2. Primary: Queries local database using full-text search vector and ILIKE.
    3. Disconnect Guard (Fallback): Before costly external GNews API calls, checks if client disconnected.
    4. Secondary: If 0 matches found locally and client remains connected, queries upstream GNews API,
       persists the newly fetched articles idempotently, and serves them tagged source='live_fallback'.
    5. Disconnect Guard (Exit): Checks if client disconnected before serializing and returning payload.
    Annotates search results with is_bookmarked and is_read flags if caller is authenticated.
    """
    # Guard 1: Verify client connection has not been severed prior to processing
    if await request.is_disconnected():
        logger.info(
            "Search request aborted: client disconnected prior to database lookup (query=%s, client_ip=%s)",
            q,
            getattr(request.state, "client_ip", "unknown"),
        )
        raise HTTPException(
            status_code=499,
            detail="Client Closed Request",
        )

    search_filter = _build_search_filter(db, q)

    count_query = db.query(func.count(Article.id)).filter(search_filter)
    if category:
        count_query = count_query.filter(Article.category == category.lower().strip())
    total = count_query.scalar() or 0
    source = "local"

    # Secondary stage: upstream live GNews fallback if local search yielded 0 results
    if total == 0:
        # Guard 2: Verify client has not cancelled in-flight before making external upstream HTTP call
        if await request.is_disconnected():
            logger.info(
                "Search fallback skipped: client disconnected prior to external API query (query=%s, client_ip=%s)",
                q,
                getattr(request.state, "client_ip", "unknown"),
            )
            raise HTTPException(
                status_code=499,
                detail="Client Closed Request",
            )

        gnews_client = GNewsClient()
        live_articles = await gnews_client.search_articles(q.strip())
        if live_articles:
            ArticleRepository.batch_insert_sync(
                db, live_articles, category=category or "general"
            )
            count_query = db.query(func.count(Article.id)).filter(search_filter)
            if category:
                count_query = count_query.filter(
                    Article.category == category.lower().strip()
                )
            total = count_query.scalar() or 0
            if total > 0:
                source = "live_fallback"

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    # Guard 3: Verify client connection before final ORM query and payload serialization
    if await request.is_disconnected():
        logger.info(
            "Search response aborted: client disconnected prior to response delivery (query=%s, client_ip=%s)",
            q,
            getattr(request.state, "client_ip", "unknown"),
        )
        raise HTTPException(
            status_code=499,
            detail="Client Closed Request",
        )

    if current_user:
        query = (
            db.query(
                Article,
                Bookmark.id.label("bookmark_id"),
                ArticleRead.id.label("read_id"),
            )
            .outerjoin(
                Bookmark,
                (Bookmark.article_id == Article.id)
                & (Bookmark.user_id == current_user.id),
            )
            .outerjoin(
                ArticleRead,
                (ArticleRead.article_id == Article.id)
                & (ArticleRead.user_id == current_user.id),
            )
        )
    else:
        query = db.query(
            Article,
            literal(None).label("bookmark_id"),
            literal(None).label("read_id"),
        )

    query = query.filter(search_filter)
    if category:
        query = query.filter(Article.category == category.lower().strip())

    rows = (
        query.order_by(Article.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for article, bookmark_id, read_id in rows:
        item = ArticleSearchItem(
            id=article.id,
            title=article.title,
            description=article.description,
            content=article.content,
            url=article.url,
            image_url=article.image_url,
            source_name=article.source_name,
            category=article.category,
            country=article.country,
            language=article.language,
            share_token=article.share_token,
            published_at=article.published_at,
            created_at=article.created_at,
            is_bookmarked=(bookmark_id is not None),
            is_read=(read_id is not None),
        )
        items.append(item)

    return SearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        source=source,
    )
