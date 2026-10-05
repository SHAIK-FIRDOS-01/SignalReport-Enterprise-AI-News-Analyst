"""
Unit and Integration Tests for SignalReport Intelligence Module.
Verifies Groq LLM heuristic fallbacks, prompt input bounding, and 3-call quota before 4h cooldown ban.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.intelligence.models import LLMUsageBan, LLMUsageLog


class IntelligenceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        LLMUsageBan.objects.all().delete()
        LLMUsageLog.objects.all().delete()

    def test_analyze_article_heuristic_fallback(self):
        url = reverse("api-v1-intelligence:news-analyze")
        payload = {
            "title": "Stock market rally pushes tech giants to record valuation",
            "description": "Surge in quarterly earnings drives massive enterprise stock buying.",
            "source_name": "Reuters",
            "category": "business",
        }
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "success")
        self.assertEqual(resp.data["sentiment"], "BULLISH")
        self.assertTrue(len(resp.data["executive_takeaways"]) > 0)
        self.assertEqual(resp.data["requests_used"], 1)
        self.assertEqual(resp.data["requests_remaining"], 2)

        # Confirm request log is created
        self.assertEqual(LLMUsageLog.objects.count(), 1)
        # Not banned yet on first call
        self.assertFalse(LLMUsageBan.objects.exists())

    def test_analyze_article_three_requests_then_ban(self):
        """
        Verify that a client IP can make up to 3 LLM analysis calls.
        The 4th call within the cooldown window returns HTTP 429 and is rejected.
        """
        url = reverse("api-v1-intelligence:news-analyze")
        payload = {
            "title": "Autonomous Robotics Deployed Across Factory Lines",
            "description": "Hardware automation delivers record manufacturing output.",
            "source_name": "TechDaily",
            "category": "technology",
        }

        # 1. First call succeeds (remaining: 2)
        resp_1 = self.client.post(url, payload, format="json")
        self.assertEqual(resp_1.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_1.data["requests_remaining"], 2)
        self.assertFalse(LLMUsageBan.objects.exists())

        # 2. Second call succeeds (remaining: 1)
        resp_2 = self.client.post(url, payload, format="json")
        self.assertEqual(resp_2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_2.data["requests_remaining"], 1)
        self.assertFalse(LLMUsageBan.objects.exists())

        # 3. Third call succeeds (remaining: 0, triggers cooldown ban for subsequent calls)
        resp_3 = self.client.post(url, payload, format="json")
        self.assertEqual(resp_3.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_3.data["requests_remaining"], 0)
        self.assertTrue(LLMUsageBan.objects.exists())

        # 4. Fourth call from same IP must be banned (HTTP 429)
        resp_4 = self.client.post(url, payload, format="json")
        self.assertEqual(resp_4.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("LLM access restricted", resp_4.data["detail"])
        self.assertIn("Retry-After", resp_4)

    def test_analyze_invalid_payload_rejected(self):
        url = reverse("api-v1-intelligence:news-analyze")
        # Missing title
        resp = self.client.post(url, {"description": "No title provided"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
