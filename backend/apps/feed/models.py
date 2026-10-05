"""
Feed, Article, and Interaction Models for SignalReport.
Replaces: backend/app/models/article.py, backend/app/models/interactions.py
Ponytail: Standard Django ORM models with composite unique_together and declarative indexes.
Security-audit: Cascade deletes on user removal; foreign key constraints guard referential integrity.
"""

from django.db import models
from django.conf import settings


class Article(models.Model):
    """
    Syndicated enterprise news intelligence article.
    """
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    url = models.CharField(max_length=1000, unique=True, db_index=True)
    image_url = models.CharField(max_length=1000, null=True, blank=True)
    source_name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, db_index=True)
    country = models.CharField(max_length=10, default="in")
    language = models.CharField(max_length=10, default="en")
    share_token = models.CharField(max_length=16, unique=True, db_index=True)
    published_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "articles"
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["category", "-published_at"], name="ix_art_cat_pub"),
        ]

    def __str__(self) -> str:
        return f"{self.title[:50]} ({self.category})"


class Bookmark(models.Model):
    """
    Tracks saved articles per authenticated user.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
        db_index=True,
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="bookmarked_by",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bookmarks"
        unique_together = (("user", "article"),)
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Bookmark(user={self.user_id}, article={self.article_id})"


class ArticleRead(models.Model):
    """
    Tracks article read history per authenticated user.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reads",
        db_index=True,
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="read_by",
        db_index=True,
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "article_reads"
        unique_together = (("user", "article"),)
        ordering = ["-read_at"]

    def __str__(self) -> str:
        return f"ArticleRead(user={self.user_id}, article={self.article_id})"

