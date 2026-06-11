import logging
from typing import Dict, Any
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

class NLPProcessingService:
    """
    Proxy service that forwards NLP processing requests to the FastAPI microservice.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'MICROSERVICE_URL', 'http://localhost:8001')

    async def process_content(self, text: str) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/nlp/process"
        payload = {
            "text": text
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to run NLP processing on microservice: {str(e)}")
            return {"sentiment": 0.0, "entities": [], "status": "failed", "error": str(e)}
