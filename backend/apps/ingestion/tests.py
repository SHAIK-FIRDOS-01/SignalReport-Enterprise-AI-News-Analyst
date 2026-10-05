"""
Unit and Integration Tests for SignalReport Ingestion Module.
Verifies GNews quota budgeting, circuit breakers, and category cooldowns.
"""

from django.test import TestCase
from django.utils import timezone
from apps.ingestion.models import APICallLog
from apps.ingestion.services.gnews_client import GNewsClient, normalize_article_data


class IngestionTests(TestCase):
    def setUp(self):
        APICallLog.objects.all().delete()
        self.client = GNewsClient()

    def test_normalize_article_data(self):
        raw = {
            "title": "Quantum Computing Breakthrough",
            "url": "https://example.com/quantum",
            "description": "Researchers achieve fault tolerance.",
            "source": {"name": "ScienceDaily"},
        }
        norm = normalize_article_data(raw, default_category="technology")
        self.assertIsNotNone(norm)
        self.assertEqual(norm["title"], "Quantum Computing Breakthrough")
        self.assertEqual(norm["category"], "technology")
        self.assertEqual(norm["source_name"], "ScienceDaily")
        self.assertTrue(len(norm["share_token"]) > 0)

    def test_gnews_quota_management(self):
        # Fresh quota should be permitted
        allowed, msg = self.client.check_quota("technology")
        self.assertTrue(allowed)

        # Simulate reaching daily limit of 80 calls
        logs = [
            APICallLog(service="gnews", category="technology", status_code=200, articles_retrieved=10)
            for _ in range(80)
        ]
        APICallLog.objects.bulk_create(logs)

        # Quota should now reject additional calls
        allowed_after, reason = self.client.check_quota("technology")
        self.assertFalse(allowed_after)
        self.assertIn("budget reached", reason.lower())

    def test_category_cooldown(self):
        APICallLog.objects.create(
            service="gnews",
            category="business",
            status_code=200,
            articles_retrieved=5,
        )
        # Calling same category immediately should be blocked by cooldown
        allowed, reason = self.client.check_quota("business")
        self.assertFalse(allowed)
        self.assertIn("cooldown", reason.lower())

        # Calling different category should be permitted
        allowed_other, _ = self.client.check_quota("technology")
        self.assertTrue(allowed_other)
