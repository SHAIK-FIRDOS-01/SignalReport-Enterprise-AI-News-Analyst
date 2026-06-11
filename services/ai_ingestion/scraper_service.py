import httpx
import trafilatura
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ContentScraperService:
    """
    Enterprise-grade web scraper for extracting full article content.
    Uses trafilatura for high-accuracy text extraction and httpx for resilient fetching.
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        self.timeout = 15.0

    async def scrape_full_content(self, url: str) -> Optional[str]:
        """
        Fetches the URL and extracts the main body text.
        """
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                # Use trafilatura to extract the main content
                downloaded = response.text
                content = trafilatura.extract(downloaded, include_comments=False, include_tables=True, no_fallback=False)
                
                if content:
                    # Basic cleaning: remove extra whitespace
                    content = " ".join(content.split())
                    logger.info(f"Successfully scraped {len(content)} characters from {url}")
                    return content
                
                logger.warning(f"Trafilatura failed to extract content from {url}")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error scraping {url}: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error scraping {url}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {str(e)}")
            
        return None
