from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.article import Article
from app.models.interactions import Bookmark, ArticleRead
from app.api.deps import get_optional_current_user

router = APIRouter(prefix="/news", tags=["Share"])


class SharedArticleResponse(BaseModel):
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


@router.get(
    "/share/{share_token}",
    response_model=SharedArticleResponse,
    status_code=status.HTTP_200_OK,
)
def resolve_share_token(
    share_token: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> SharedArticleResponse:
    """
    Resolves a publicly accessible shared article via its unique cryptographically secure share_token.
    If accessed by an authenticated user, annotates personal bookmark and read statuses.
    Raises 404 if the share token does not correspond to an existing article.
    """
    clean_token = share_token.strip()

    if current_user:
        row = (
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
            .filter(Article.share_token == clean_token)
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared article not found.",
            )
        article, bookmark_id, read_id = row
        is_bookmarked = bookmark_id is not None
        is_read = read_id is not None
    else:
        article = db.query(Article).filter(Article.share_token == clean_token).first()
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared article not found.",
            )
        is_bookmarked = False
        is_read = False

    return SharedArticleResponse(
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
        is_bookmarked=is_bookmarked,
        is_read=is_read,
    )
