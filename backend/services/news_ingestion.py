import logging
from typing import List, Dict, Any
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

class NewsIngestionService:
    """
    Proxy service that forwards news fetching requests to the FastAPI microservice.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'MICROSERVICE_URL', 'http://localhost:8001')

    async def fetch_news(
        self, 
        query: str = "AI advancements", 
        lang: str = "en", 
        max_results: int = 10,
        from_date: str = None,
        to_date: str = None
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url.rstrip('/')}/news/fetch"
        payload = {
            "query": query,
            "lang": lang,
            "max_results": max_results,
            "from_date": from_date,
            "to_date": to_date
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                return data.get("articles", [])
        except Exception as e:
            logger.error(f"Failed to fetch news from microservice: {str(e)}")
            return []

    async def fetch_top_headlines(
        self, 
        category: str = "general", 
        lang: str = "en", 
        country: str = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url.rstrip('/')}/news/headlines"
        payload = {
            "category": category,
            "lang": lang,
            "country": country,
            "max_results": max_results
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                return data.get("articles", [])
        except Exception as e:
            logger.error(f"Failed to fetch headlines from microservice: {str(e)}")
            return []
