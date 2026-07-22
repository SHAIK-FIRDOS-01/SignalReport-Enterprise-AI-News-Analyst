import os
import logging
import json
import asyncio
from typing import Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)

class AIService:
    """
    Enterprise-grade AI service powered by Groq (Llama 3).
    Optimized for extremely fast inference and high rate limits.
    """
    
    def __init__(self):
        self.api_key = os.getenv('GROQ_API_KEY')
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
            # Llama 3.3 70B for high-quality, 8B for extreme speed
            self.model = "llama-3.3-70b-versatile" 
        else:
            self.client = None
            logger.error("CRITICAL: GROQ_API_KEY is missing.")

    def _sanitize_input(self, text: str) -> str:
        return text.replace('\n', ' ').strip()

    async def _safe_generate(self, prompt: str, system_prompt: str = "You are a professional news analyst."):
        """
        Internal helper to call Groq asynchronously.
        """
        if not self.client:
            raise Exception("AI Model not initialized")
            
        loop = asyncio.get_event_loop()
        
        def call_groq():
            return self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
                response_format={"type": "json_object"} if "JSON" in prompt else None,
                temperature=0.2,
                max_tokens=2048,
            )

        return await loop.run_in_executor(None, call_groq)

    async def enhance_and_vectorize(self, content: str, nlp_context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.client:
            return self._fallback_response(content)

        sanitized_content = self._sanitize_input(content[:15000])
        
        prompt = f"""
        Analyze the following news article in depth. Provide a professional, comprehensive, and highly structured summary.
        Sentiment Context: {nlp_context.get('sentiment', 0)}
        Entities identified: {', '.join(nlp_context.get('entities', []))}
        
        Article Content:
        {sanitized_content}
        
        Return the result strictly as a JSON object with these keys:
        - enhanced_content: string (clear, multi-paragraph analysis)
        - credibility_score: float (0.0 to 1.0)
        - vector_representation: array of 5 floats (representing topical clusters)
        """

        try:
            response = await self._safe_generate(prompt)
            result_text = response.choices[0].message.content.strip()
            parsed_data = json.loads(result_text)
            
            return {
                'enhanced_content': parsed_data.get('enhanced_content', content[:500]),
                'credibility_score': parsed_data.get('credibility_score', 0.5),
                'vector': parsed_data.get('vector_representation', [0.1, 0.2, 0.3, 0.4, 0.5])
            }
            
        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")
            return self._fallback_response(content, f"Analysis temporarily unavailable: {str(e)[:50]}")

    def _fallback_response(self, content: str, message: str = "Fallback Analysis") -> Dict[str, Any]:
        return {
            'enhanced_content': f"{message}: {content[:300]}...",
            'credibility_score': 0.1,
            'vector': [0.0] * 5
        }

    async def explain_term(self, term: str, context: str) -> str:
        if not self.client: return "AI Unavailable."
        prompt = f"""
        Provide a professional definition for the term '{term}'. 
        First, give a clear general definition. 
        Then, briefly explain its significance within the following context if relevant:
        ---
        {context[:5000]}
        ---
        Keep the entire response under 60 words.
        """
        try:
            response = await self._safe_generate(prompt)
            return response.choices[0].message.content.strip()
        except Exception:
            return "Definition temporarily unavailable."

    async def answer_question(self, question: str, context: str, source_url: str = None) -> str:
        if not self.client: return "AI Unavailable."
        
        source_text = f"\nSource URL: {source_url}" if source_url else ""
        prompt = f"""
        Using ONLY this context, answer the question.
        You MUST cite your source by appending a markdown link to any facts you state, like so: [Source]({source_url if source_url else 'url'}).
        
        Context: '{context[:15000]}'{source_text}
        
        Question: '{question}'
        """
        try:
            response = await self._safe_generate(prompt)
            return response.choices[0].message.content.strip()
        except Exception:
            return "I'm currently over-capacity. Please try again in a moment."

    async def generate_briefing(self, articles: list) -> str:
        if not self.client: return "AI Unavailable."
        
        articles_text = ""
        for idx, art in enumerate(articles):
            articles_text += f"\n--- Article {idx+1}: {art.get('title')} ---\nSource URL: {art.get('source_url', '#')}\n{art.get('content')[:3000]}\n"
            
        prompt = f"""
        You are a senior enterprise intelligence analyst. Write a high-level executive briefing consolidating the following articles:
        {articles_text}
        
        Provide a professional, clean Markdown report containing:
        1. **Executive Summary**: A high-level overview of the news.
        2. **Consensus & Conflicts**: Where the articles agree or disagree.
        3. **Key Takeaways & Impact**: Business or technology impact of this information.
        
        CRITICAL RULE: You MUST cite your sources using inline Markdown links (e.g., `[Title of Article](URL)`) whenever you mention facts or summarize points from the articles.
        
        Keep it professional, well-formatted, and concise. Do not include introductory or concluding conversational text.
        """
        try:
            response = await self._safe_generate(prompt)
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Failed to generate briefing: {str(e)}"
