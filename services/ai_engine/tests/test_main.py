import os
import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

root_dir = Path(__file__).resolve().parent.parent.parent.parent
ai_engine_dir = root_dir / "services" / "ai_engine"

for p in [str(root_dir), str(ai_engine_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from services.ai_engine.main import app
from services.ai_engine.config import settings


@pytest.mark.asyncio
async def test_health_check_unauthenticated():
    """Verify /health returns 200 OK and status 'healthy' without auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert data.get("service") == "ai_engine"


@pytest.mark.asyncio
async def test_enrich_rejects_missing_key():
    """Verify /api/v1/enrich rejects calls without X-Internal-Service-Key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Llama 3.3 Released",
            "content": "Meta releases Llama 3.3 70B with 128k context.",
            "source_url": "https://ai.meta.com/blog/llama-3-3/"
        }
        response = await client.post("/api/v1/enrich", json=payload)
        assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_enrich_rejects_invalid_key():
    """Verify /api/v1/enrich rejects calls with invalid X-Internal-Service-Key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Llama 3.3 Released",
            "content": "Meta releases Llama 3.3 70B with 128k context.",
            "source_url": "https://ai.meta.com/blog/llama-3-3/"
        }
        response = await client.post(
            "/api/v1/enrich",
            json=payload,
            headers={"X-Internal-Service-Key": "wrong-key-value"}
        )
        assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_enrich_success_with_valid_key():
    """Verify /api/v1/enrich returns 200 OK and structured intelligence payload with valid key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Llama 3.3 Released",
            "content": "Meta releases Llama 3.3 70B with 128k context.",
            "source_url": "https://ai.meta.com/blog/llama-3-3/"
        }
        valid_key = settings.INTERNAL_SERVICE_KEY
        response = await client.post(
            "/api/v1/enrich",
            json=payload,
            headers={"X-Internal-Service-Key": valid_key}
        )
        assert response.status_code == 200, f"Got status {response.status_code}: {response.text}"
        data = response.json()
        assert "enhanced_content" in data
        assert "signal_type" in data
        assert "credibility_score" in data
        assert "vector" in data
        assert len(data["vector"]) == 384
        assert "metadata_json" in data
