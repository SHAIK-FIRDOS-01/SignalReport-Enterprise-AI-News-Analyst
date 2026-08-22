import logging
from typing import Optional
import httpx
from django.conf import settings
from core.security.anti_ssrf import validate_url_anti_ssrf, SSRFValidationError

logger = logging.getLogger(__name__)


class ContentScraperService:
    """
    Proxy service that forwards scraping requests to the FastAPI microservice.
    Enforces Anti-SSRF URL validation and attaches cryptographic X-Internal-Service-Key.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'MICROSERVICE_URL', 'http://localhost:8001')
        self.internal_service_key = getattr(settings, 'INTERNAL_SERVICE_KEY', '')

    def get_auth_headers(self):
        key = getattr(settings, 'INTERNAL_SERVICE_KEY', self.internal_service_key)
        return {
            "X-Internal-Service-Key": key,
            "Content-Type": "application/json"
        }

    async def scrape_full_content(self, url: str) -> Optional[str]:
        # 1. Anti-SSRF validation
        try:
            validated_url = validate_url_anti_ssrf(url)
        except SSRFValidationError as e:
            logger.warning(f"Anti-SSRF blocked scraping request for {url}: {e}")
            return None

        target_url = f"{self.base_url.rstrip('/')}/scraper/scrape"
        payload = {
            "url": validated_url
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    target_url,
                    json=payload,
                    headers=self.get_auth_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("content")
        except Exception as e:
            logger.error(f"Failed to scrape content from microservice for {url}: {str(e)}")
            return None
