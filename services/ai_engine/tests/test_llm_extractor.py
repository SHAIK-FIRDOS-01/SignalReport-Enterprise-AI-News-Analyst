import os
import sys
import json
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

root_dir = Path(__file__).resolve().parent.parent.parent.parent
ai_engine_dir = root_dir / "services" / "ai_engine"

for p in [str(root_dir), str(ai_engine_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from services.ai_engine.llm_extractor import LLMExtractorService, ExtractedSignalData


@pytest.mark.asyncio
async def test_groq_structured_json_extraction_success():
    """Verify LLMExtractorService extracts structured JSON from Groq Llama 3.3 70B."""
    service = LLMExtractorService()
    
    mock_groq_json = {
        "summary": "Meta releases Llama 3.3 70B with 128k context window matching 405B capabilities.",
        "signal_type": "LAUNCH",
        "credibility_score": 0.95,
        "key_takeaways": [
            "128k context window support",
            "State of the art open weights performance",
            "Quantized FP8 inference available"
        ],
        "entities": ["Meta", "Llama 3.3", "PyTorch"],
        "structured_metadata": {
            "model_size": "70B",
            "context_window": "128k",
            "license": "Llama 3.3 Community"
        }
    }
    
    with patch.object(service, "_call_groq", new_callable=AsyncMock) as mock_groq:
        mock_groq.return_value = mock_groq_json
        
        result = await service.extract_signal_intelligence(
            title="Llama 3.3 70B Released",
            content="Meta today launched Llama 3.3 70B...",
            source_url="https://ai.meta.com/blog/llama-3-3"
        )
        
        assert isinstance(result, ExtractedSignalData)
        assert result.signal_type == "LAUNCH"
        assert result.credibility_score == 0.95
        assert len(result.key_takeaways) == 3
        assert "Meta" in result.entities
        assert result.structured_metadata["model_size"] == "70B"
        assert mock_groq.called


@pytest.mark.asyncio
async def test_groq_fallback_to_openrouter_on_failure():
    """Verify LLMExtractorService falls back to OpenRouter when Groq returns 500/rate limits."""
    service = LLMExtractorService()
    
    mock_openrouter_json = {
        "summary": "Anthropic introduces Claude 3.5 Haiku with high speed and coding benchmarks.",
        "signal_type": "LAUNCH",
        "credibility_score": 0.90,
        "key_takeaways": ["Fast latency", "Strong coding capabilities"],
        "entities": ["Anthropic", "Claude 3.5 Haiku"],
        "structured_metadata": {"latency": "sub-100ms"}
    }
    
    with patch.object(service, "_call_groq", new_callable=AsyncMock) as mock_groq:
        mock_groq.side_effect = Exception("Groq 503 Service Unavailable / Rate Limit Exceeded")
        
        with patch.object(service, "_call_openrouter", new_callable=AsyncMock) as mock_openrouter:
            mock_openrouter.return_value = mock_openrouter_json
            
            result = await service.extract_signal_intelligence(
                title="Anthropic Launches Claude 3.5 Haiku",
                content="Anthropic today announced Haiku 3.5...",
                source_url="https://anthropic.com/news/haiku-3-5"
            )
            
            assert isinstance(result, ExtractedSignalData)
            assert result.signal_type == "LAUNCH"
            assert result.provider == "openrouter"
            assert "Anthropic" in result.entities
            assert mock_openrouter.called


@pytest.mark.asyncio
async def test_heuristic_fallback_when_all_providers_fail():
    """Verify LLMExtractorService returns deterministic fallback payload if all LLMs fail."""
    service = LLMExtractorService()
    
    with patch.object(service, "_call_groq", new_callable=AsyncMock) as mock_groq:
        mock_groq.side_effect = Exception("Groq Offline")
        with patch.object(service, "_call_openrouter", new_callable=AsyncMock) as mock_openrouter:
            mock_openrouter.side_effect = Exception("OpenRouter Quota Exhausted")
            
            result = await service.extract_signal_intelligence(
                title="AI Startup Raises $30M Series A",
                content="Startup X has raised $30 million led by Sequoia Capital.",
                source_url="https://techcrunch.com/startup-x-funding"
            )
            
            assert isinstance(result, ExtractedSignalData)
            assert result.provider == "heuristic_fallback"
            assert result.signal_type == "FUNDING"
            assert result.credibility_score > 0.0
            assert len(result.key_takeaways) >= 1
