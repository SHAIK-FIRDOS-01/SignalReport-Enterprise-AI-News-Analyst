import os
import json
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import httpx

try:
    from .config import settings
except ImportError:
    from config import settings

logger = logging.getLogger("ai_engine.llm_extractor")


class ExtractedSignalData(BaseModel):
    summary: str = Field(..., description="2-3 sentence executive intelligence briefing")
    signal_type: str = Field(default="GENERAL", description="Taxonomy classification ('LAUNCH', 'FUNDING', 'RESEARCH', 'UPGRADE', 'BUZZ', 'GENERAL')")
    credibility_score: float = Field(default=0.85, description="Source reliability score (0.0 to 1.0)")
    key_takeaways: List[str] = Field(default_factory=list, description="Bullet point analytical takeaways")
    entities: List[str] = Field(default_factory=list, description="Key companies, people, technologies, and models")
    structured_metadata: Dict[str, Any] = Field(default_factory=dict, description="Extracted metrics (funding amounts, model params, benchmarks)")
    provider: str = Field(default="groq", description="LLM provider that generated the intelligence extraction")


SYSTEM_PROMPT = """You are an elite enterprise AI & Technology Intelligence Analyst.
Analyze the provided tech news signal or paper and output strict valid JSON with the following keys:
{
  "summary": "2-3 sentence high-impact executive summary",
  "signal_type": "One of: LAUNCH, FUNDING, RESEARCH, UPGRADE, BUZZ, GENERAL",
  "credibility_score": 0.95,
  "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
  "entities": ["Company", "Model", "Person"],
  "structured_metadata": {"key": "value"}
}
Taxonomy Guidelines:
- LAUNCH: New model, product, framework, or company launch.
- FUNDING: Venture capital rounds, seed, series funding, acquisitions, valuations.
- RESEARCH: New scientific papers, arXiv preprints, benchmark breakthroughs.
- UPGRADE: New software versions, API improvements, security deprecations, outages.
- BUZZ: Community discussions, viral debates, opinions.
- GENERAL: Other tech industry signals.
"""


class LLMExtractorService:
    """
    High-throughput structured intelligence extraction engine using Groq Llama 3.3 70B
    with automated OpenRouter and heuristic fallback pipelines.
    """

    def __init__(self):
        self.groq_api_key = getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
        self.openrouter_api_key = getattr(settings, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")

    async def _call_groq(self, user_content: str) -> Dict[str, Any]:
        """Calls Groq Llama 3.3 70B in JSON mode."""
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")

        from groq import AsyncGroq
        client = AsyncGroq(api_key=self.groq_api_key)
        
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1024
        )
        content = response.choices[0].message.content
        return json.loads(content)

    async def _call_openrouter(self, user_content: str) -> Dict[str, Any]:
        """Calls OpenRouter endpoint in JSON mode as secondary fallback."""
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")

        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://signalreport.internal",
                "X-Title": "SignalReport AI Engine"
            }
            body = {
                "model": "meta-llama/llama-3.3-70b-instruct",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            res = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
            res.raise_for_status()
            data = res.json()
            raw_json = data["choices"][0]["message"]["content"]
            return json.loads(raw_json)

    def _heuristic_extract(self, title: str, content: str, source_url: Optional[str] = None) -> ExtractedSignalData:
        """Deterministic heuristic fallback when all external LLM APIs fail."""
        text_lower = (title + " " + content).lower()
        signal_type = "GENERAL"
        if any(k in text_lower for k in ("launch", "release", "announc", "unveil", "open source")):
            signal_type = "LAUNCH"
        elif any(k in text_lower for k in ("fund", "seed", "series a", "series b", "million", "billion", "valuation", "invest")):
            signal_type = "FUNDING"
        elif any(k in text_lower for k in ("paper", "arxiv", "research", "benchmark", "accuracy", "mmlu")):
            signal_type = "RESEARCH"
        elif any(k in text_lower for k in ("upgrade", "v1.", "v2.", "v3.", "deprecated", "outage", "patch")):
            signal_type = "UPGRADE"
        elif any(k in text_lower for k in ("hn", "reddit", "viral", "debate", "community")):
            signal_type = "BUZZ"

        clean_snippet = (content[:250] + "...") if len(content) > 250 else content
        return ExtractedSignalData(
            summary=f"Analysis of signal: {title}. {clean_snippet}",
            signal_type=signal_type,
            credibility_score=0.80,
            key_takeaways=[
                title,
                f"Classified taxonomy: {signal_type}",
                f"Source: {source_url or 'Direct'}"
            ],
            entities=["Technology"],
            structured_metadata={"source_url": source_url, "fallback": True},
            provider="heuristic_fallback"
        )

    async def extract_signal_intelligence(
        self,
        title: str,
        content: str,
        source_url: Optional[str] = None
    ) -> ExtractedSignalData:
        """
        Execute signal intelligence extraction pipeline with multi-provider resilience.
        """
        user_content = f"Title: {title}\nURL: {source_url or ''}\n\nContent:\n{content[:4000]}"

        # 1. Primary: Groq Llama 3.3 70B
        try:
            raw_data = await self._call_groq(user_content)
            data = ExtractedSignalData(**raw_data, provider="groq")
            return data
        except Exception as groq_err:
            logger.warning(f"Primary Groq extraction failed ({groq_err}). Attempting OpenRouter fallback...")

        # 2. Secondary: OpenRouter
        try:
            raw_data = await self._call_openrouter(user_content)
            data = ExtractedSignalData(**raw_data, provider="openrouter")
            return data
        except Exception as openrouter_err:
            logger.warning(f"Secondary OpenRouter extraction failed ({openrouter_err}). Activating heuristic fallback...")

        # 3. Tertiary: Heuristic Fallback
        return self._heuristic_extract(title, content, source_url)
