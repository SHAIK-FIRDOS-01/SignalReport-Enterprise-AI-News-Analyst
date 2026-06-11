import logging
from typing import Optional
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

class ContentScraperService:
    """
    Proxy service that forwards scraping requests to the FastAPI microservice.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'MICROSERVICE_URL', 'http://localhost:8001')

    async def scrape_full_content(self, url: str) -> Optional[str]:
        target_url = f"{self.base_url.rstrip('/')}/scraper/scrape"
        payload = {
            "url": url
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(target_url, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                return data.get("content")
        except Exception as e:
            logger.error(f"Failed to scrape content from microservice for {url}: {str(e)}")
            return None
