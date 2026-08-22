import logging
from typing import Dict, Any, List
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class AIService:
    """
    Proxy service that forwards AI enhancement, glossary, and Q&A tasks to the FastAPI microservice.
    Attaches cryptographic X-Internal-Service-Key header for zero-trust inter-service authentication.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'MICROSERVICE_URL', 'http://localhost:8001')
        self.internal_service_key = getattr(settings, 'INTERNAL_SERVICE_KEY', '')

    def get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers containing the internal service shared secret."""
        key = getattr(settings, 'INTERNAL_SERVICE_KEY', self.internal_service_key)
        return {
            "X-Internal-Service-Key": key,
            "Content-Type": "application/json"
        }

    async def enhance_and_vectorize(self, content: str, nlp_context: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/ai/enhance"
        payload = {
            "content": content,
            "nlp_context": nlp_context
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.get_auth_headers(),
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to enhance/vectorize on microservice: {str(e)}")
            return {
                'enhanced_content': f"Fallback Analysis: {content[:300]}...",
                'credibility_score': 0.1,
                'signal_type': 'GENERAL',
                'vector': [0.0] * 384
            }

    async def explain_term(self, term: str, context: str) -> str:
        url = f"{self.base_url.rstrip('/')}/ai/explain-term"
        payload = {
            "term": term,
            "context": context
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.get_auth_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("definition", "Definition temporarily unavailable.")
        except Exception as e:
            logger.error(f"Failed to explain term via microservice: {str(e)}")
            return "Definition temporarily unavailable."

    async def answer_question(self, question: str, context: str) -> str:
        url = f"{self.base_url.rstrip('/')}/ai/ask-question"
        payload = {
            "question": question,
            "context": context
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.get_auth_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("answer", "I'm currently over-capacity. Please try again in a moment.")
        except Exception as e:
            logger.error(f"Failed to answer question via microservice: {str(e)}")
            return "I'm currently over-capacity. Please try again in a moment."

    async def generate_briefing(self, articles: List[Dict[str, Any]]) -> str:
        url = f"{self.base_url.rstrip('/')}/ai/synthesize"
        payload = {
            "articles": articles
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.get_auth_headers(),
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("briefing", "Briefing generation failed.")
        except Exception as e:
            logger.error(f"Failed to generate briefing via microservice: {str(e)}")
            return "Briefing generation failed."
