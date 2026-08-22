import os
import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

# Set up paths
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
ai_engine_dir = root_dir / "services" / "ai_engine"

for p in [str(root_dir), str(backend_dir), str(ai_engine_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from django.conf import settings
from services.ai_engine.main import app
from services.ai_engine.security import verify_internal_service_key
from backend.services.ai_service import AIService


@pytest.mark.asyncio
async def test_fastapi_rejects_missing_internal_service_key():
    """Verify FastAPI returns 403 Forbidden when X-Internal-Service-Key is omitted on protected endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/ai/enhance", json={"content": "test", "nlp_context": {}})
        assert response.status_code in (401, 403), f"Expected 401/403, got {response.status_code}"


@pytest.mark.asyncio
async def test_fastapi_rejects_invalid_internal_service_key():
    """Verify FastAPI returns 403 Forbidden when X-Internal-Service-Key is invalid."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ai/enhance",
            json={"content": "test", "nlp_context": {}},
            headers={"X-Internal-Service-Key": "invalid-secret-key-123"}
        )
        assert response.status_code in (401, 403), f"Expected 401/403, got {response.status_code}"


@pytest.mark.asyncio
async def test_fastapi_accepts_valid_internal_service_key():
    """Verify FastAPI returns 200 OK when valid X-Internal-Service-Key header is supplied."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        valid_key = os.getenv("INTERNAL_SERVICE_KEY", "signalreport_enterprise_internal_shared_secret_2026")
        response = await client.post(
            "/ai/enhance",
            json={"content": "OpenAI announces new model", "nlp_context": {}},
            headers={"X-Internal-Service-Key": valid_key}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


def test_django_ai_service_attaches_internal_service_key():
    """Verify Django AIService includes X-Internal-Service-Key header matching django settings."""
    service = AIService()
    headers = service.get_auth_headers()
    assert "X-Internal-Service-Key" in headers
    expected_key = getattr(settings, 'INTERNAL_SERVICE_KEY', None)
    assert expected_key is not None
    assert headers["X-Internal-Service-Key"] == expected_key
