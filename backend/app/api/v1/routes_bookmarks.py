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

router = APIRouter(prefix="/news", tags=["Bookmarks"])


class BookmarkActionResponse(BaseModel):
    bookmarked: bool
    article_id: int
    message: str


class ArticleBookmarkItem(BaseModel):
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
    bookmarked_at: datetime
    is_bookmarked: bool = True
    is_read: bool = False


class BookmarkListResponse(BaseModel):
    items: List[ArticleBookmarkItem]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.post(
    "/articles/{article_id}/bookmark",
    response_model=BookmarkActionResponse,
    status_code=status.HTTP_200_OK,
)
def bookmark_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookmarkActionResponse:
    """
    Saves an article to user's personal bookmarks.
    Enforces idempotency: returns success if already bookmarked.
    """
    article = db.query(Article).filter_by(id=article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found.",
        )

    existing = (
        db.query(Bookmark)
        .filter_by(user_id=current_user.id, article_id=article_id)
        .first()
    )
    if existing:
        return BookmarkActionResponse(
            bookmarked=True,
            article_id=article_id,
            message="Article already bookmarked.",
        )

    bookmark = Bookmark(user_id=current_user.id, article_id=article_id)
    db.add(bookmark)
    try:
        db.commit()
        db.refresh(bookmark)
    except IntegrityError:
        db.rollback()

    return BookmarkActionResponse(
        bookmarked=True,
        article_id=article_id,
        message="Article bookmarked successfully.",
    )


@router.delete(
    "/articles/{article_id}/bookmark",
    response_model=BookmarkActionResponse,
    status_code=status.HTTP_200_OK,
)
def unbookmark_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookmarkActionResponse:
    """
    Removes an article from user's personal bookmarks.
    Enforces idempotency: returns success if article was not bookmarked.
    """
    article = db.query(Article).filter_by(id=article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found.",
        )

    bookmark = (
        db.query(Bookmark)
        .filter_by(user_id=current_user.id, article_id=article_id)
        .first()
    )
    if bookmark:
        db.delete(bookmark)
        db.commit()
        return BookmarkActionResponse(
            bookmarked=False,
            article_id=article_id,
            message="Article bookmark removed successfully.",
        )

    return BookmarkActionResponse(
        bookmarked=False,
        article_id=article_id,
        message="Article was not bookmarked.",
    )


@router.delete(
    "/bookmarks/{id}",
    response_model=BookmarkActionResponse,
    status_code=status.HTTP_200_OK,
)
def delete_bookmark_by_id(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookmarkActionResponse:
    """
    Deletes a bookmark enforcing compound SQL ownership:
    WHERE (bookmark.id = :id OR bookmark.article_id = :id) AND bookmark.user_id = :current_user.id.
    If rowcount is 0, strictly raises HTTP 404 NOT FOUND (never 403) to prevent ID enumeration probing.
    """
    bookmark = (
        db.query(Bookmark)
        .filter(
            ((Bookmark.id == id) | (Bookmark.article_id == id))
            & (Bookmark.user_id == current_user.id)
        )
        .first()
    )
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found.",
        )

    article_id = bookmark.article_id
    db.delete(bookmark)
    db.commit()
    return BookmarkActionResponse(
        bookmarked=False,
        article_id=article_id,
        message="Article bookmark removed successfully.",
    )


@router.get(
    "/bookmarks/{id}",
    response_model=ArticleBookmarkItem,
    status_code=status.HTTP_200_OK,
)
def get_bookmark_by_id(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ArticleBookmarkItem:
    """
    Inspects a private bookmark enforcing compound SQL ownership:
    WHERE (bookmark.id = :id OR bookmark.article_id = :id) AND bookmark.user_id = :current_user.id.
    If rowcount is 0, strictly raises HTTP 404 NOT FOUND (never 403) to prevent ID enumeration probing.
    """
    row = (
        db.query(
            Article,
            Bookmark.created_at.label("bookmarked_at"),
            ArticleRead.id.label("read_id"),
        )
        .join(
            Bookmark,
            (Bookmark.article_id == Article.id)
            & (Bookmark.user_id == current_user.id),
        )
        .outerjoin(
            ArticleRead,
            (ArticleRead.article_id == Article.id)
            & (ArticleRead.user_id == current_user.id),
        )
        .filter(
            ((Bookmark.id == id) | (Bookmark.article_id == id))
            & (Bookmark.user_id == current_user.id)
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found.",
        )

    article, bookmarked_at, read_id = row
    return ArticleBookmarkItem(
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
        bookmarked_at=bookmarked_at,
        is_bookmarked=True,
        is_read=(read_id is not None),
    )


@router.get(
    "/bookmarks",
    response_model=BookmarkListResponse,
    status_code=status.HTTP_200_OK,
)
def list_bookmarks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookmarkListResponse:
    """
    Retrieves paginated list of articles bookmarked by the authenticated user,
    ordered in reverse chronological order of bookmark creation time.
    Annotates each article with is_bookmarked=True and read telemetry is_read.
    """
    total = (
        db.query(func.count(Bookmark.id))
        .filter(Bookmark.user_id == current_user.id)
        .scalar()
        or 0
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    rows = (
        db.query(
            Article,
            Bookmark.created_at.label("bookmarked_at"),
            ArticleRead.id.label("read_id"),
        )
        .join(
            Bookmark,
            (Bookmark.article_id == Article.id)
            & (Bookmark.user_id == current_user.id),
        )
        .outerjoin(
            ArticleRead,
            (ArticleRead.article_id == Article.id)
            & (ArticleRead.user_id == current_user.id),
        )
        .order_by(Bookmark.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for article, bookmarked_at, read_id in rows:
        item = ArticleBookmarkItem(
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
            bookmarked_at=bookmarked_at,
            is_bookmarked=True,
            is_read=(read_id is not None),
        )
        items.append(item)

    return BookmarkListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
