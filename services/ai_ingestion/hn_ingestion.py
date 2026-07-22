import httpx
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class HackerNewsIngestionService:
    """
    Service for fetching news from the Hacker News Firebase API asynchronously.
    """
    
    def __init__(self):
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.max_retries = 3

    async def _fetch_json(self, client: httpx.AsyncClient, url: str) -> Any:
        for attempt in range(self.max_retries):
            try:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP error on {url}: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    return None
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                return None

    async def _fetch_item(self, client: httpx.AsyncClient, item_id: int) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/item/{item_id}.json"
        item = await self._fetch_json(client, url)
        
        if not item or item.get('deleted') or item.get('dead') or item.get('type') != 'story':
            return None
            
        # Format to match our internal representation
        published_at = None
        if item.get('time'):
            published_at = datetime.fromtimestamp(item['time'], tz=timezone.utc).isoformat()
            
        source_url = item.get('url') or f"https://news.ycombinator.com/item?id={item_id}"
            
        return {
            "title": item.get('title', ''),
            "description": "",
            "content": item.get('text', ''),
            "url": source_url,
            "image": "",  # HN doesn't provide images
            "publishedAt": published_at,
            "source": {
                "name": "Hacker News",
                "url": "https://news.ycombinator.com"
            },
            "hn_id": item_id,
            "score": item.get('score', 0)
        }

    async def _fetch_stories(self, endpoint: str, limit: int = 10) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{endpoint}.json"
        
        async with httpx.AsyncClient() as client:
            story_ids = await self._fetch_json(client, url)
            if not story_ids:
                return []
                
            story_ids = story_ids[:limit]
            
            # Fetch all items concurrently
            tasks = [self._fetch_item(client, item_id) for item_id in story_ids]
            results = await asyncio.gather(*tasks)
            
            # Filter out None values (deleted/dead/non-story items)
            return [item for item in results if item is not None]

    async def fetch_top_stories(self, limit: int = 10) -> List[Dict[str, Any]]:
        return await self._fetch_stories("topstories", limit)

    async def fetch_new_stories(self, limit: int = 10) -> List[Dict[str, Any]]:
        return await self._fetch_stories("newstories", limit)

    async def fetch_best_stories(self, limit: int = 10) -> List[Dict[str, Any]]:
        return await self._fetch_stories("beststories", limit)
