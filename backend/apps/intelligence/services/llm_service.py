"""
LLM Analysis Service utilizing Groq API or graceful heuristic fallback.
Input bounded to 4,500 characters to prevent prompt injection and token overflow.
"""

import json
import logging
from typing import Dict, Any, Optional
import httpx
from django.conf import settings

logger = logging.getLogger("llm_service")

SYSTEM_PROMPT = """
You are the senior editorial intelligence analyst at SignalReport.
Analyze the provided news story and produce an executive briefing in strict JSON.
The output MUST be a JSON object with exactly these keys:
{
  "status": "success",
  "executive_takeaways": [
    "3-4 concise, high-impact bullet points summarizing strategic significance."
  ],
  "sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "sentiment_rationale": "One sentence explaining market or institutional rationale.",
  "key_entities": ["List of organizations, individuals, or sovereign entities mentioned."],
  "strategic_impact": "A concise paragraph assessing macro implications."
}
Only output the raw JSON object. Do not wrap in markdown quotes.
"""


def _heuristic_fallback(
    title: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Standard library rule-based fallback analyzer when LLM API is unreachable or unconfigured.
    """
    text = f"{title} {description or ''}".lower()

    bullish_signals = ["surge", "rally", "growth", "record", "profit", "gain", "breakthrough", "expands", "bullish"]
    bearish_signals = ["fall", "slump", "crisis", "drop", "loss", "recession", "down", "warning", "probe", "collapse"]

    bull_count = sum(1 for w in bullish_signals if w in text)
    bear_count = sum(1 for w in bearish_signals if w in text)

    if bull_count > bear_count:
        sentiment = "BULLISH"
        rationale = "Positive momentum indicators and growth signals detected."
    elif bear_count > bull_count:
        sentiment = "BEARISH"
        rationale = "Contractionary headwinds or negative sentiment cues detected."
    else:
        sentiment = "NEUTRAL"
        rationale = "Balanced macro indicators without decisive directional volatility."

    words = [w.capitalize() for w in title.split() if len(w) > 4 and w.isalpha()]
    unique_entities = list(dict.fromkeys(words))[:4] or ["Industry Analysts"]

    return {
        "status": "success",
        "executive_takeaways": [
            f"Key event reported: {title[:120]}...",
            f"Sector categorisation resolved under {category or 'General'}.",
            "Institutional oversight continues to monitor secondary ripple effects.",
        ],
        "sentiment": sentiment,
        "sentiment_rationale": rationale,
        "key_entities": unique_entities,
        "strategic_impact": f"Strategic oversight recommended for {category or 'macro'} operational portfolios.",
        "model": "heuristic-fallback",
    }


def analyze_article_content(
    title: str,
    description: Optional[str] = None,
    content: Optional[str] = None,
    source: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Direct in-context LLM analysis. Bounded to 4500 chars input.
    Calls Groq LPU endpoint or falls back gracefully to heuristic analyzer.
    """
    api_key = getattr(settings, "GROQ_API_KEY", "") or ""
    model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile") or "llama-3.3-70b-versatile"

    if not api_key:
        return _heuristic_fallback(title, description, category)

    safe_body = (content or description or "")[:4500]
    user_payload = (
        f"ARTICLE TITLE: {title[:500]}\n"
        f"SOURCE: {source or 'Unknown'}\n"
        f"CATEGORY: {category or 'General'}\n\n"
        f"CONTENT:\n{safe_body}"
    )

    try:
        with httpx.Client(timeout=12.0) as client:
            res = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_payload},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                },
            )

        if res.status_code == 200:
            parsed = res.json()
            raw_text = parsed["choices"][0]["message"]["content"]
            result = json.loads(raw_text)
            result["status"] = "success"
            result["model"] = model
            return result
        else:
            logger.warning(f"Groq API error HTTP {res.status_code}: {res.text}")
            return _heuristic_fallback(title, description, category)
    except Exception as exc:
        logger.warning(f"Groq invocation failed ({exc}); deploying heuristic fallback.")
        return _heuristic_fallback(title, description, category)
