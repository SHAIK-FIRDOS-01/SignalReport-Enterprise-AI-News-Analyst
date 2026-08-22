import logging
from typing import Optional
import httpx
import trafilatura

try:
    from .security_ssrf import validate_url_anti_ssrf, SSRFValidationError
except ImportError:
    from security_ssrf import validate_url_anti_ssrf, SSRFValidationError

logger = logging.getLogger("ai_engine.scraper")


class ContentScraperService:
    """
    High-accuracy, Anti-SSRF protected web scraper for tech news, research, and documentation.
    Uses trafilatura for main body text extraction with 10.0s timeouts and Anti-SSRF gatekeeping.
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36 SignalReport/1.0'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def extract_clean_content(self, html: str) -> Optional[str]:
        """
        Extract clean main body text/markdown from raw HTML, stripping ads, nav bars, and boilerplate.
        """
        if not html:
            return None
            
        try:
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                output_format='txt'
            )
            if extracted:
                # Clean consecutive whitespace
                cleaned = " ".join(extracted.split())
                return cleaned
        except Exception as e:
            logger.error(f"Trafilatura extraction error: {e}")

        return None

    async def scrape_full_content(self, url: str, raise_on_ssrf: bool = False) -> Optional[str]:
        """
        Validates URL against Anti-SSRF rules, fetches HTML, and returns cleaned article body.
        """
        # 1. Anti-SSRF URL Validation
        try:
            validated_url = validate_url_anti_ssrf(url)
        except SSRFValidationError as e:
            logger.warning(f"Anti-SSRF blocked scraping request for '{url}': {e}")
            if raise_on_ssrf:
                raise
            return None
        except Exception as e:
            logger.warning(f"Invalid URL for scraping '{url}': {e}")
            if raise_on_ssrf:
                raise SSRFValidationError(str(e))
            return None

        # 2. Fetch and Extract
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                response = await client.get(validated_url, timeout=self.timeout)
                response.raise_for_status()
                return self.extract_clean_content(response.text)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} scraping {url}")
        except httpx.RequestError as e:
            logger.error(f"Request network error scraping {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")

        return None
