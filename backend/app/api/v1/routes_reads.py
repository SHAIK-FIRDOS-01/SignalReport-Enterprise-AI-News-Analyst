import math
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.models.user import User
from app.models.article import Article
from app.models.interactions import Bookmark, ArticleRead
from app.api.deps import get_current_user

router = APIRouter(prefix="/news", tags=["Read Status"])


class ReadActionResponse(BaseModel):
    read: bool
    article_id: int
    message: str


class ArticleReadItem(BaseModel):
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
    read_at: datetime
    is_read: bool = True
    is_bookmarked: bool = False


class ReadListResponse(BaseModel):
    items: List[ArticleReadItem]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.post(
    "/articles/{article_id}/read",
    response_model=ReadActionResponse,
    status_code=status.HTTP_200_OK,
)
def mark_article_as_read(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReadActionResponse:
    """
    Marks an article as read for the authenticated user.
    Enforces idempotency: returns success if already marked as read.
    """
    article = db.query(Article).filter_by(id=article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found.",
        )

    existing = (
        db.query(ArticleRead)
        .filter_by(user_id=current_user.id, article_id=article_id)
        .first()
    )
    if existing:
        return ReadActionResponse(
            read=True,
            article_id=article_id,
            message="Article already marked as read.",
        )

    read_record = ArticleRead(user_id=current_user.id, article_id=article_id)
    db.add(read_record)
    try:
        db.commit()
        db.refresh(read_record)
    except IntegrityError:
        db.rollback()

    return ReadActionResponse(
        read=True,
        article_id=article_id,
        message="Article marked as read.",
    )


@router.delete(
    "/articles/{article_id}/read",
    response_model=ReadActionResponse,
    status_code=status.HTTP_200_OK,
)
def mark_article_as_unread(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReadActionResponse:
    """
    Removes read status for an article, marking it as unread.
    Enforces idempotency: returns success if article was not marked as read.
    """
    article = db.query(Article).filter_by(id=article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found.",
        )

    read_record = (
        db.query(ArticleRead)
        .filter_by(user_id=current_user.id, article_id=article_id)
        .first()
    )
    if read_record:
        db.delete(read_record)
        db.commit()
        return ReadActionResponse(
            read=False,
            article_id=article_id,
            message="Article marked as unread.",
        )

    return ReadActionResponse(
        read=False,
        article_id=article_id,
        message="Article was not marked as read.",
    )


@router.get(
    "/reads",
    response_model=ReadListResponse,
    status_code=status.HTTP_200_OK,
)
def list_reads(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReadListResponse:
    """
    Retrieves paginated list of articles read by the authenticated user,
    ordered in reverse chronological order of read timestamp.
    Annotates each article with is_read=True and saved state is_bookmarked.
    """
    total = (
        db.query(func.count(ArticleRead.id))
        .filter(ArticleRead.user_id == current_user.id)
        .scalar()
        or 0
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    rows = (
        db.query(
            Article,
            ArticleRead.read_at.label("read_at"),
            Bookmark.id.label("bookmark_id"),
        )
        .join(
            ArticleRead,
            (ArticleRead.article_id == Article.id)
            & (ArticleRead.user_id == current_user.id),
        )
        .outerjoin(
            Bookmark,
            (Bookmark.article_id == Article.id)
            & (Bookmark.user_id == current_user.id),
        )
        .order_by(ArticleRead.read_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for article, read_at, bookmark_id in rows:
        item = ArticleReadItem(
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
            read_at=read_at,
            is_read=True,
            is_bookmarked=(bookmark_id is not None),
        )
        items.append(item)

    return ReadListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
