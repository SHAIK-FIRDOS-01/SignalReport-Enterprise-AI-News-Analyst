"""
Feed, Search, Bookmark, Read, and Analysis URL routing.
"""

from django.urls import path
from .views import (
    FeedView,
    BookmarkListCreateView,
    BookmarkDetailDeleteView,
    ArticleBookmarkToggleView,
    ReadListCreateView,
    ArticleReadToggleView,
    ReadDeleteView,
    ShareArticleView,
)

app_name = "feed"

urlpatterns = [
    # Feed routes
    path("feed/", FeedView.as_view(), name="feed"),
    path("news/feed/", FeedView.as_view(), name="news-feed"),

    # Bookmark collection routes
    path("bookmarks/", BookmarkListCreateView.as_view(), name="bookmarks"),
    path("news/bookmarks/", BookmarkListCreateView.as_view(), name="news-bookmarks"),

    # Bookmark item routes (by id or article_id)
    path("bookmarks/<int:id>/", BookmarkDetailDeleteView.as_view(), name="bookmark-detail"),
    path("news/bookmarks/<int:id>/", BookmarkDetailDeleteView.as_view(), name="news-bookmark-detail"),

    # Article bookmark toggle routes
    path("articles/<int:article_id>/bookmark/", ArticleBookmarkToggleView.as_view(), name="article-bookmark"),
    path("news/articles/<int:article_id>/bookmark/", ArticleBookmarkToggleView.as_view(), name="news-article-bookmark"),

    # Read history collection routes
    path("reads/", ReadListCreateView.as_view(), name="reads"),
    path("news/reads/", ReadListCreateView.as_view(), name="news-reads"),

    # Read item delete routes
    path("reads/<int:article_id>/", ReadDeleteView.as_view(), name="read-detail"),
    path("news/reads/<int:article_id>/", ReadDeleteView.as_view(), name="news-read-detail"),

    # Article read toggle routes
    path("articles/<int:article_id>/read/", ArticleReadToggleView.as_view(), name="article-read"),
    path("news/articles/<int:article_id>/read/", ArticleReadToggleView.as_view(), name="news-article-read"),

    # Share token routes
    path("news/share/<str:share_token>/", ShareArticleView.as_view(), name="news-share-detail"),
    path("share/<str:share_token>/", ShareArticleView.as_view(), name="share-detail"),
]

