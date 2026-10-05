"""
Unit, Integration, and Security Audit Tests for SignalReport Feed and Interactivity Modules.
Replaces: backend/tests/test_routes_*.py, test_security_*.py, test_interaction_models.py
Ponytail: Direct DRF APIClient and Django TestCase checking query efficiency and status codes.
Security-audit: IDOR verification, N+1 optimization verification, security headers, Cloudflare edge IP spoofing defense.
"""

from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.feed.models import Article, Bookmark, ArticleRead
from core.security import is_trusted_peer, resolve_client_ip

User = get_user_model()


class FeedTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.user_a = User.objects.create_user(email="usera@signalreport.io", password="Password123!", is_verified=True)
        self.user_b = User.objects.create_user(email="userb@signalreport.io", password="Password123!", is_verified=True)

        token_a = str(RefreshToken.for_user(self.user_a).access_token)
        self.auth_client_a = APIClient()
        self.auth_client_a.credentials(HTTP_AUTHORIZATION=f"Bearer {token_a}")

        token_b = str(RefreshToken.for_user(self.user_b).access_token)
        self.auth_client_b = APIClient()
        self.auth_client_b.credentials(HTTP_AUTHORIZATION=f"Bearer {token_b}")

        # Articles
        now = timezone.now()
        self.article_1 = Article.objects.create(
            title="AI Revolution in Enterprise Computing",
            description="DeepMind announces revolutionary neural architecture for enterprise scaling.",
            content="Full dispatch content covering compute benchmarks and model efficiency.",
            url="https://example.com/ai-revolution-enterprise",
            source_name="TechWire",
            category="technology",
            country="in",
            language="en",
            share_token="tech_share_001",
            published_at=now,
        )

        self.article_2 = Article.objects.create(
            title="Central Bank Announces Macro Policy Shifts",
            description="Global banking consortium tightens liquidity guidelines amid inflation reports.",
            content="Monetary policy analysis across sovereign debt instruments.",
            url="https://example.com/macro-policy-shifts",
            source_name="Financial Gazette",
            category="business",
            country="in",
            language="en",
            share_token="biz_share_002",
            published_at=now - timedelta(hours=1),
        )

        self.article_3 = Article.objects.create(
            title="General News Dispatch Summary",
            description="Daily overview of national logistics and infrastructure developments.",
            content="Infrastructure investment figures released by the ministry.",
            url="https://example.com/general-dispatch",
            source_name="Reuters",
            category="general",
            country="in",
            language="en",
            share_token="gen_share_003",
            published_at=now - timedelta(hours=2),
        )

        # Interactions for User A
        self.bookmark_a = Bookmark.objects.create(user=self.user_a, article=self.article_1)
        self.read_a = ArticleRead.objects.create(user=self.user_a, article=self.article_1)

    def test_feed_anonymous(self):
        url = reverse("api-v1-feed:feed")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 3)
        self.assertEqual(len(response.data["items"]), 3)

        # Anonymous caller must see is_bookmarked=False and is_read=False
        for item in response.data["items"]:
            self.assertFalse(item["is_bookmarked"])
            self.assertFalse(item["is_read"])

    def test_feed_authenticated_annotated(self):
        url = reverse("api-v1-feed:feed")
        response = self.auth_client_a.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        items_by_id = {item["id"]: item for item in response.data["items"]}
        # Article 1 is bookmarked and read by User A
        self.assertTrue(items_by_id[self.article_1.id]["is_bookmarked"])
        self.assertTrue(items_by_id[self.article_1.id]["is_read"])

        # Article 2 is neither bookmarked nor read by User A
        self.assertFalse(items_by_id[self.article_2.id]["is_bookmarked"])
        self.assertFalse(items_by_id[self.article_2.id]["is_read"])

    def test_feed_category_filter(self):
        url = reverse("api-v1-feed:feed")
        response = self.client.get(url, {"category": "technology"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["items"][0]["category"], "technology")

    def test_feed_all_filter(self):
        url = reverse("api-v1-feed:feed")
        response = self.client.get(url, {"category": "ALL"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 3)


    def test_n_plus_1_query_optimization(self):
        """
        Verify that fetching feeds executes a bounded constant number of queries
        even as articles scale (using prefetch_related for user bookmarks and reads).
        """
        # Create 10 additional articles
        now = timezone.now()
        bulk_arts = [
            Article(
                title=f"Batch Article {i}",
                description=f"Batch description {i}",
                url=f"https://example.com/batch-{i}",
                source_name="Wire",
                category="technology",
                share_token=f"token_{i}",
                published_at=now,
            )
            for i in range(10)
        ]
        Article.objects.bulk_create(bulk_arts)

        url = reverse("api-v1-feed:feed")
        # 1 user auth, 1 count, 1 articles, 1 bookmarked_by prefetch, 1 read_by prefetch = 5 queries strictly bounded!
        with self.assertNumQueries(5):
            response = self.auth_client_a.get(url, {"page_size": 20})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["total"], 13)


    def test_bookmark_list_create(self):
        url = reverse("api-v1-feed:bookmarks")
        # User A already bookmarked article 1
        resp = self.auth_client_a.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total"], 1)
        self.assertEqual(resp.data["items"][0]["id"], self.article_1.id)

        # Create bookmark for article 2 via JSON body
        create_resp = self.auth_client_a.post(url, {"article_id": self.article_2.id}, format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(create_resp.data["bookmarked"])

        # Duplicate create is idempotent
        dup_resp = self.auth_client_a.post(url, {"article_id": self.article_2.id}, format="json")
        self.assertEqual(dup_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(dup_resp.data["bookmarked"])

    def test_article_bookmark_toggle_post_delete(self):
        toggle_url = reverse("api-v1-feed:article-bookmark", kwargs={"article_id": self.article_3.id})
        # Toggle on (POST)
        resp = self.auth_client_a.post(toggle_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["bookmarked"])

        # Toggle off (DELETE)
        del_resp = self.auth_client_a.delete(toggle_url)
        self.assertEqual(del_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(del_resp.data["bookmarked"])

    def test_idor_bookmark_defense(self):
        """
        Adversarial test: User B attempts to access or delete User A's bookmark.
        Enforces strict HTTP 404 NOT FOUND (never 403) to prevent enumeration probing.
        """
        # User A owns bookmark_a (ID matches self.bookmark_a.id or article_1.id)
        idor_url = reverse("api-v1-feed:news-bookmark-detail", kwargs={"id": self.bookmark_a.id})

        # User B GET request must raise 404
        get_resp = self.auth_client_b.get(idor_url)
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

        # User B DELETE request must raise 404
        del_resp = self.auth_client_b.delete(idor_url)
        self.assertEqual(del_resp.status_code, status.HTTP_404_NOT_FOUND)

        # Confirm User A's bookmark is untouched in the database
        self.assertTrue(Bookmark.objects.filter(id=self.bookmark_a.id).exists())

    def test_read_list_create_and_delete(self):
        reads_url = reverse("api-v1-feed:reads")
        list_resp = self.auth_client_a.get(reads_url)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(list_resp.data["total"], 1)

        # Mark article 2 read
        create_resp = self.auth_client_a.post(reads_url, {"article_id": self.article_2.id}, format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(create_resp.data["read"])

        # Delete read record
        del_url = reverse("api-v1-feed:read-detail", kwargs={"article_id": self.article_2.id})
        del_resp = self.auth_client_a.delete(del_url)
        self.assertEqual(del_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(del_resp.data["read"])

    def test_share_article(self):
        url = reverse("api-v1-feed:news-share-detail", kwargs={"share_token": "tech_share_001"})
        # Public access
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["title"], self.article_1.title)

        # Invalid token returns 404
        bad_url = reverse("api-v1-feed:news-share-detail", kwargs={"share_token": "non_existent"})
        bad_resp = self.client.get(bad_url)
        self.assertEqual(bad_resp.status_code, status.HTTP_404_NOT_FOUND)


    def test_health_check(self):
        url = reverse("health-check")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "healthy")

    def test_security_headers_enforced(self):
        url = reverse("health-check")
        resp = self.client.get(url)
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resp["X-Frame-Options"], "DENY")
        self.assertIn("max-age=31536000", resp["Strict-Transport-Security"])
        self.assertIn("default-src 'self'", resp["Content-Security-Policy"])

    def test_cloudflare_trusted_proxy_evaluation(self):
        # Known Cloudflare IP is trusted
        self.assertTrue(is_trusted_peer("173.245.48.5"))
        # Localhost is trusted
        self.assertTrue(is_trusted_peer("127.0.0.1"))
        # Untrusted public IP is not trusted
        self.assertFalse(is_trusted_peer("8.8.8.8"))
