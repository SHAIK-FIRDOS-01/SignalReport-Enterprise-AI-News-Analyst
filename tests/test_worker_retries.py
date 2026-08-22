import os
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

# Set up paths
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"

for p in [str(root_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from core.resilience import (
    calculate_backoff_with_jitter,
    route_to_dlq,
    get_dlq_messages,
    DLQ_REDIS_KEY,
)
from apps.knowledge_base.tasks import resilient_scrape_article_task


def test_exponential_backoff_with_jitter_calculation():
    """Verify exponential backoff 2^retries + jitter produces correct non-deterministic intervals."""
    b0 = calculate_backoff_with_jitter(retries=0)
    assert 1.0 <= b0 <= 2.0
    
    b1 = calculate_backoff_with_jitter(retries=1)
    assert 2.0 <= b1 <= 3.0
    
    b3 = calculate_backoff_with_jitter(retries=3)
    assert 8.0 <= b3 <= 9.0
    
    samples = [calculate_backoff_with_jitter(retries=2) for _ in range(10)]
    assert len(set(samples)) > 1, "Jitter must introduce randomization"


def test_dlq_routing_and_retrieval():
    """Verify failed tasks are routed to Dead Letter Queue with diagnostics."""
    fake_payload = {"article_url": "https://example.com/blocked", "attempt": 5}
    error_msg = "HTTP 429: Upstream rate limit permanently exhausted"
    
    msg_id = route_to_dlq(
        task_name="resilient_scrape_article_task",
        payload=fake_payload,
        error=error_msg
    )
    assert msg_id is not None
    
    messages = get_dlq_messages()
    assert len(messages) >= 1
    latest = messages[0]
    assert latest["task_name"] == "resilient_scrape_article_task"
    assert latest["payload"] == fake_payload
    assert error_msg in latest["error"]


def test_resilient_scrape_task_retries_on_rate_limit():
    """Verify resilient task invokes retry with exponential backoff on HTTP 429."""
    import httpx
    
    with patch.object(resilient_scrape_article_task, 'retry', side_effect=Exception("CeleryRetryTriggered")) as mock_retry:
        with patch("apps.knowledge_base.tasks.ContentScraperService") as MockService:
            instance = MockService.return_value
            req = httpx.Request("GET", "https://api.example.com")
            resp = httpx.Response(429, request=req)
            instance.scrape_full_content.side_effect = httpx.HTTPStatusError("Rate limited", request=req, response=resp)
            
            with pytest.raises(Exception) as exc_info:
                resilient_scrape_article_task("https://api.example.com/art1")
            
            assert "CeleryRetryTriggered" in str(exc_info.value)
            assert mock_retry.called
            call_kwargs = mock_retry.call_args[1]
            assert "countdown" in call_kwargs
            # For initial retry retries=0, 2^0 + jitter = 1.x
            assert 1.0 <= call_kwargs["countdown"] <= 2.0
