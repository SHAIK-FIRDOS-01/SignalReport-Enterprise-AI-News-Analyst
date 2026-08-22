import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

root_dir = Path(__file__).resolve().parent.parent.parent.parent
ai_engine_dir = root_dir / "services" / "ai_engine"

for p in [str(root_dir), str(ai_engine_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from services.ai_engine.scraper_service import ContentScraperService
from services.ai_engine.security_ssrf import SSRFValidationError


def test_extract_clean_content_from_html():
    """Verify ContentScraperService strips navigation, ads, and extracts clean body text."""
    scraper = ContentScraperService()
    raw_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Tech Launch News</title></head>
    <body>
        <nav><a href="/home">Home</a><a href="/login">Login</a></nav>
        <div class="ad-banner">Buy Cheap Cloud Credits Now!</div>
        <article>
            <h1>DeepSeek-V3 Open Source Architecture Announced</h1>
            <p>DeepSeek-AI has officially released DeepSeek-V3, a state-of-the-art 671B parameter Mixture-of-Experts language model.</p>
            <p>The architecture features Multi-Head Latent Attention (MLA) and DeepSeekMoE with auxiliary-loss-free load balancing.</p>
        </article>
        <footer>Copyright 2026 TechMedia Inc. Privacy Policy.</footer>
    </body>
    </html>
    """
    clean_text = scraper.extract_clean_content(raw_html)
    assert clean_text is not None
    assert "DeepSeek-V3 Open Source Architecture Announced" in clean_text
    assert "Multi-Head Latent Attention" in clean_text
    assert "Buy Cheap Cloud Credits Now!" not in clean_text


@pytest.mark.asyncio
async def test_scraper_blocks_ssrf_urls():
    """Verify scraper rejects localhost and cloud metadata URLs before connecting."""
    scraper = ContentScraperService()
    blocked_urls = [
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:8080/internal",
        "http://127.0.0.1:9000/keys",
        "http://10.0.0.5/secrets",
    ]
    for url in blocked_urls:
        with pytest.raises(SSRFValidationError):
            await scraper.scrape_full_content(url, raise_on_ssrf=True)
            
        # Verify safe mode returns None without raising
        result = await scraper.scrape_full_content(url, raise_on_ssrf=False)
        assert result is None


@pytest.mark.asyncio
async def test_scraper_fetches_and_extracts_safe_url():
    """Verify scraper fetches HTML from safe public URL with 10s timeout and extracts content."""
    scraper = ContentScraperService()
    assert scraper.timeout == 10.0
    
    mock_html = """
    <html>
        <body>
            <article>
                <h1>Groq LPU Accelerates Inference to 500 T/s</h1>
                <p>Groq's Tensor Streaming Processor delivers ultra-fast deterministic token generation for real-time applications.</p>
            </article>
        </body>
    </html>
    """
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        content = await scraper.scrape_full_content("https://example.com/groq-update")
        assert content is not None
        assert "Groq LPU Accelerates Inference" in content
