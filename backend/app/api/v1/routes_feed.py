import math
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, literal
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.article import Article
from app.models.interactions import Bookmark, ArticleRead
from app.api.deps import get_optional_current_user

router = APIRouter(prefix="/news", tags=["Feed"])


class ArticleFeedItem(BaseModel):
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


class FeedResponse(BaseModel):
    items: List[ArticleFeedItem]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get(
    "/feed",
    response_model=FeedResponse,
    status_code=status.HTTP_200_OK,
)
def get_news_feed(
    category: Optional[str] = Query(None, description="Filter articles by news vertical"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> FeedResponse:
    """
    Serves paginated news intelligence articles ordered newest first by publication date.
    Supports optional category filtering.
    For authenticated readers, dynamically annotates whether each article has been
    bookmarked or read. For anonymous readers, interaction flags default to False.
    """
    count_query = db.query(func.count(Article.id))
    if category:
        count_query = count_query.filter(Article.category == category.lower().strip())
    total = count_query.scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

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
        item = ArticleFeedItem(
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

    return FeedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
