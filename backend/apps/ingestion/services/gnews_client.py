"""
GNews API Client for SignalReport Ingestion Pipeline.
Enforces daily call budget (max 80/24h) and 90m per-category cooldown.
"""

import time
import secrets
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from django.conf import settings

logger = logging.getLogger("gnews_client")


def normalize_article_data(
    item: Dict[str, Any],
    default_category: str = "general",
    country: str = "in",
    language: str = "en",
) -> Optional[Dict[str, Any]]:
    """
    Normalizes raw article dictionaries into schema-compliant mappings.
    Generates a cryptographically secure URL-safe share_token.
    """
    title = item.get("title")
    url = item.get("url")
    if not title or not url:
        return None

    raw_pub = item.get("published_at") or item.get("publishedAt")
    if isinstance(raw_pub, datetime):
        pub_dt = raw_pub
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
    elif isinstance(raw_pub, str):
        try:
            cleaned_str = raw_pub.replace("Z", "+00:00")
            pub_dt = datetime.fromisoformat(cleaned_str)
        except Exception:
            pub_dt = datetime.now(timezone.utc)
    else:
        pub_dt = datetime.now(timezone.utc)

    source_val = item.get("source_name")
    if not source_val:
        src = item.get("source")
        if isinstance(src, dict):
            source_val = src.get("name", "Unknown")
        elif isinstance(src, str):
            source_val = src
        else:
            source_val = "Unknown"

    share_token = item.get("share_token") or secrets.token_urlsafe(8)

    return {
        "title": str(title)[:500],
        "description": item.get("description"),
        "content": item.get("content"),
        "url": str(url)[:1000],
        "image_url": item.get("image_url") or item.get("image"),
        "source_name": str(source_val)[:100],
        "category": str(item.get("category") or default_category).lower()[:50],
        "country": str(item.get("country") or country)[:10],
        "language": str(item.get("language") or language)[:10],
        "share_token": str(share_token)[:16],
        "published_at": pub_dt,
    }


class GNewsClient:
    """
    Client for querying the GNews API.
    Enforces inter-request pacing and daily budget bounds via APICallLog.
    """
    _last_request_time: float = 0.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        inter_request_delay: float = 1.2,
        timeout: float = 10.0,
    ):
        self.api_key = api_key or getattr(settings, "GNEWS_API_KEY", "")
        self.base_url = (base_url or getattr(settings, "GNEWS_BASE_URL", "https://gnews.io/api/v4")).rstrip("/")
        self.inter_request_delay = inter_request_delay
        self.timeout = timeout

    def _throttle(self) -> None:
        """Enforces mandatory inter-request delay across calls."""
        now = time.monotonic()
        elapsed = now - GNewsClient._last_request_time
        if GNewsClient._last_request_time > 0 and elapsed < self.inter_request_delay:
            time.sleep(self.inter_request_delay - elapsed)
        GNewsClient._last_request_time = time.monotonic()

    @staticmethod
    def check_quota(category: str, force: bool = False) -> tuple[bool, str]:
        """
        Validates GNews API call eligibility against daily budget (max 100/day, capped at 80)
        and per-category cooldown window (default 90 mins).
        """
        if force:
            return True, "Force bypass enabled."

        from django.utils import timezone
        from datetime import timedelta
        from apps.ingestion.models import APICallLog

        now = timezone.now()
        day_ago = now - timedelta(hours=24)

        # 1. Daily Quota Guard (80 calls / 24h)
        daily_limit = getattr(settings, "GNEWS_MAX_DAILY_CALLS", 80)
        daily_count = APICallLog.objects.filter(service="gnews", timestamp__gte=day_ago).count()
        if daily_count >= daily_limit:
            return False, f"Daily GNews budget reached ({daily_count}/{daily_limit} calls in 24h). Quota preserved."

        # 2. Circuit Breaker on recent 429
        six_hours_ago = now - timedelta(hours=6)
        has_recent_429 = APICallLog.objects.filter(
            service="gnews", status_code=429, timestamp__gte=six_hours_ago
        ).exists()
        if has_recent_429:
            return False, "Circuit breaker active: GNews returned HTTP 429 in past 6h. Pausing requests."

        # 3. Category Cooldown Guard (default 90 minutes)
        cooldown_mins = getattr(settings, "GNEWS_CATEGORY_COOLDOWN_MINUTES", 90)
        cooldown_threshold = now - timedelta(minutes=cooldown_mins)
        last_cat_call = (
            APICallLog.objects.filter(
                service="gnews",
                category=category.lower().strip(),
                timestamp__gte=cooldown_threshold,
            )
            .order_by("-timestamp")
            .first()
        )
        if last_cat_call:
            elapsed_mins = int((now - last_cat_call.timestamp).total_seconds() / 60)
            return False, f"Category '{category}' in cooldown (fetched {elapsed_mins}m ago, limit is {cooldown_mins}m)."

        return True, "OK"

    def fetch_top_headlines(self, category: str = "general", force: bool = False) -> List[Dict[str, Any]]:
        """
        Fetches top headlines for a given category with daily quota and cooldown enforcement.
        Logs every outbound request to APICallLog.
        """
        from apps.ingestion.models import APICallLog

        clean_cat = category.lower().strip()
        allowed, reason = self.check_quota(clean_cat, force=force)
        if not allowed:
            logger.info(f"Skipping GNews fetch for '{clean_cat}': {reason}")
            return []

        if not self.api_key:
            logger.warning("GNews API key not configured; skipping upstream fetch.")
            return []

        self._throttle()

        params = {
            "category": clean_cat,
            "country": "in",
            "lang": "en",
            "max": 10,
            "apikey": self.api_key,
        }
        url = f"{self.base_url}/top-headlines"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params=params)

                articles = []
                status_code = resp.status_code

                if status_code == 200:
                    articles = resp.json().get("articles", [])
                    logger.info(f"Fetched {len(articles)} articles for category '{clean_cat}'")
                elif status_code == 429:
                    logger.warning(f"GNews HTTP 429 rate limit exceeded for '{clean_cat}'.")
                else:
                    logger.error(f"GNews API returned {status_code}: {resp.text}")

                try:
                    APICallLog.objects.create(
                        service="gnews",
                        category=clean_cat,
                        status_code=status_code,
                        articles_retrieved=len(articles),
                    )
                except Exception as log_err:
                    logger.warning(f"Failed to record APICallLog: {log_err}")

                return articles
        except Exception as exc:
            logger.warning(f"Network error querying GNews for '{clean_cat}': {exc}")
            return []
