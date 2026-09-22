import time
import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import get_settings

logger = logging.getLogger("gnews_client")


class GNewsClient:
    """
    Asynchronous client for querying the GNews API.
    Enforces inter-request pacing (1.2s delay) to comply with upstream rate limits
    and handles HTTP 429 and network failures gracefully.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        inter_request_delay: float = 1.2,
        timeout: float = 10.0,
    ):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.GNEWS_API_KEY
        self.base_url = (base_url or settings.GNEWS_BASE_URL).rstrip("/")
        self.inter_request_delay = inter_request_delay
        self.timeout = timeout
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def _throttle(self) -> None:
        """
        Enforces a mandatory inter-request delay (default 1.2s) between consecutive calls
        to respect upstream API rate pacing requirements.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if self._last_request_time > 0 and elapsed < self.inter_request_delay:
                sleep_time = self.inter_request_delay - elapsed
                await asyncio.sleep(sleep_time)
            self._last_request_time = time.monotonic()

    async def fetch_top_headlines(self, category: str = "general") -> List[Dict[str, Any]]:
        """
        Fetches top headlines for a given category with mandatory parameters:
        country=in, lang=en, max=10, category={category}, apikey={apikey}.
        Gracefully handles HTTP 429 without raising exceptions.
        """
        await self._throttle()

        params = {
            "category": category,
            "country": "in",
            "lang": "en",
            "max": 10,
            "apikey": self.api_key,
        }

        url = f"{self.base_url}/top-headlines"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    logger.info(f"Successfully fetched {len(articles)} articles for category '{category}'")
                    return articles
                elif response.status_code == 429:
                    logger.warning(
                        f"GNews rate limit exceeded (HTTP 429) while fetching category '{category}'. "
                        f"Backing off gracefully."
                    )
                    return []
                else:
                    logger.error(f"GNews API returned non-200 status {response.status_code}: {response.text}")
                    return []
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning(f"Network error while fetching GNews top headlines for '{category}': {exc}")
            return []
        except Exception as exc:
            logger.error(f"Unexpected error while fetching GNews top headlines: {exc}")
            return []

    async def fetch_categories(self, categories: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Sequentially queries top headlines across multiple categories with rate pacing.
        """
        results: Dict[str, List[Dict[str, Any]]] = {}
        for category in categories:
            articles = await self.fetch_top_headlines(category=category)
            results[category] = articles
        return results

    async def search_articles(self, query: str) -> List[Dict[str, Any]]:
        """
        Queries GNews search endpoint with full-text fallback parameters:
        q={query}, in=title, country=in, lang=en, max=10, apikey={apikey}.
        """
        await self._throttle()

        params = {
            "q": query,
            "in": "title",
            "country": "in",
            "lang": "en",
            "max": 10,
            "apikey": self.api_key,
        }

        url = f"{self.base_url}/search"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    return data.get("articles", [])
                elif response.status_code == 429:
                    logger.warning("GNews rate limit exceeded (HTTP 429) during search query. Backing off gracefully.")
                    return []
                else:
                    logger.error(f"GNews search returned non-200 status {response.status_code}: {response.text}")
                    return []
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning(f"Network error during GNews search query '{query}': {exc}")
            return []
        except Exception as exc:
            logger.error(f"Unexpected error during GNews search query: {exc}")
            return []
