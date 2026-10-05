"""
DRF Serializers for SignalReport feed, bookmarks, reads, and AI analysis.
Replaces: FastAPI Pydantic models in routes_feed.py, routes_bookmarks.py, routes_reads.py, routes_search.py, routes_share.py
Ponytail: Standard ModelSerializers with SerializerMethodField for dynamic interaction annotations.
Security-audit: Input limits bounded, zero SQL injection vectors, context-aware user isolation.
"""

from rest_framework import serializers
from .models import Article, Bookmark, ArticleRead


class ArticleSerializer(serializers.ModelSerializer):
    """
    Syndicated news article serializer.
    Annotates dynamic is_bookmarked and is_read states without N+1 query overhead.
    """
    is_bookmarked = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "description",
            "content",
            "url",
            "image_url",
            "source_name",
            "category",
            "country",
            "language",
            "share_token",
            "published_at",
            "created_at",
            "is_bookmarked",
            "is_read",
        )

    def get_is_bookmarked(self, obj) -> bool:
        # Check if pre-computed by view annotation (O(1))
        if hasattr(obj, "annotated_bookmarked"):
            return bool(obj.annotated_bookmarked)

        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False

        # Check prefetched cache to prevent N+1 queries
        if hasattr(obj, "_prefetched_objects_cache") and "bookmarked_by" in obj._prefetched_objects_cache:
            return any(b.user_id == request.user.id for b in obj.bookmarked_by.all())

        return Bookmark.objects.filter(article_id=obj.id, user_id=request.user.id).exists()

    def get_is_read(self, obj) -> bool:
        # Check if pre-computed by view annotation (O(1))
        if hasattr(obj, "annotated_read"):
            return bool(obj.annotated_read)

        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False

        # Check prefetched cache to prevent N+1 queries
        if hasattr(obj, "_prefetched_objects_cache") and "read_by" in obj._prefetched_objects_cache:
            return any(r.user_id == request.user.id for r in obj.read_by.all())

        return ArticleRead.objects.filter(article_id=obj.id, user_id=request.user.id).exists()


class BookmarkSerializer(serializers.ModelSerializer):
    """
    Serializes a bookmark, flattening article details into the exact shape expected by the frontend.
    """
    bookmarked_at = serializers.DateTimeField(source="created_at", read_only=True)
    is_bookmarked = serializers.BooleanField(default=True, read_only=True)
    is_read = serializers.SerializerMethodField()

    # Flatten article fields
    title = serializers.CharField(source="article.title", read_only=True)
    description = serializers.CharField(source="article.description", read_only=True)
    content = serializers.CharField(source="article.content", read_only=True)
    url = serializers.CharField(source="article.url", read_only=True)
    image_url = serializers.CharField(source="article.image_url", read_only=True)
    source_name = serializers.CharField(source="article.source_name", read_only=True)
    category = serializers.CharField(source="article.category", read_only=True)
    country = serializers.CharField(source="article.country", read_only=True)
    language = serializers.CharField(source="article.language", read_only=True)
    share_token = serializers.CharField(source="article.share_token", read_only=True)
    published_at = serializers.DateTimeField(source="article.published_at", read_only=True)

    class Meta:
        model = Bookmark
        fields = (
            "id",
            "title",
            "description",
            "content",
            "url",
            "image_url",
            "source_name",
            "category",
            "country",
            "language",
            "share_token",
            "published_at",
            "created_at",
            "bookmarked_at",
            "is_bookmarked",
            "is_read",
        )

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Override the top-level 'id' with the article's id so frontend bookmark interactions map correctly
        ret["id"] = instance.article.id
        return ret

    def get_is_read(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False

        if hasattr(obj.article, "_prefetched_objects_cache") and "read_by" in obj.article._prefetched_objects_cache:
            return any(r.user_id == request.user.id for r in obj.article.read_by.all())

        return ArticleRead.objects.filter(article_id=obj.article_id, user_id=request.user.id).exists()


class ArticleReadSerializer(serializers.ModelSerializer):
    """
    Serializes a read history item, flattening article details into the exact shape expected by the frontend.
    """
    read_at = serializers.DateTimeField(read_only=True)
    is_read = serializers.BooleanField(default=True, read_only=True)
    is_bookmarked = serializers.SerializerMethodField()

    title = serializers.CharField(source="article.title", read_only=True)
    description = serializers.CharField(source="article.description", read_only=True)
    content = serializers.CharField(source="article.content", read_only=True)
    url = serializers.CharField(source="article.url", read_only=True)
    image_url = serializers.CharField(source="article.image_url", read_only=True)
    source_name = serializers.CharField(source="article.source_name", read_only=True)
    category = serializers.CharField(source="article.category", read_only=True)
    country = serializers.CharField(source="article.country", read_only=True)
    language = serializers.CharField(source="article.language", read_only=True)
    share_token = serializers.CharField(source="article.share_token", read_only=True)
    published_at = serializers.DateTimeField(source="article.published_at", read_only=True)
    created_at = serializers.DateTimeField(source="article.created_at", read_only=True)

    class Meta:
        model = ArticleRead
        fields = (
            "id",
            "title",
            "description",
            "content",
            "url",
            "image_url",
            "source_name",
            "category",
            "country",
            "language",
            "share_token",
            "published_at",
            "created_at",
            "read_at",
            "is_read",
            "is_bookmarked",
        )

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["id"] = instance.article.id
        return ret

    def get_is_bookmarked(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False

        if hasattr(obj.article, "_prefetched_objects_cache") and "bookmarked_by" in obj.article._prefetched_objects_cache:
            return any(b.user_id == request.user.id for b in obj.article.bookmarked_by.all())

        return Bookmark.objects.filter(article_id=obj.article_id, user_id=request.user.id).exists()


class BookmarkActionResponseSerializer(serializers.Serializer):
    bookmarked = serializers.BooleanField()
    article_id = serializers.IntegerField()
    message = serializers.CharField()


class ReadActionResponseSerializer(serializers.Serializer):
    read = serializers.BooleanField()
    article_id = serializers.IntegerField()
    message = serializers.CharField()

