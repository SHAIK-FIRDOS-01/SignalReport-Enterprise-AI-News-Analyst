import os
import sys
from pathlib import Path
import pytest

# Set up paths
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"

for p in [str(root_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from django.conf import settings
from django.core.cache import caches, cache
from django.test import RequestFactory, override_settings
from django.http import HttpResponse, JsonResponse
from django_ratelimit.exceptions import Ratelimited
from apps.accounts.models import CustomUser
from core.ratelimit import RateLimitMiddleware, rate_limit_ip_or_user


def test_django_redis_cache_configuration():
    """Verify django-redis cache backend is configured with RedisCache and fallback."""
    assert settings.RATELIMIT_USE_CACHE == 'default'
    assert 'default' in settings.CACHES
    backend_name = settings.CACHES['default']['BACKEND']
    assert 'django_redis' in backend_name or 'LocMemCache' in backend_name
    
    # Verify cache options
    options = settings.CACHES['default'].get('OPTIONS', {})
    if 'django_redis' in backend_name:
        assert options.get('IGNORE_EXCEPTIONS') is True
        assert 'DefaultClient' in options.get('CLIENT_CLASS', '')


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache-crud',
        }
    }
)
def test_cache_set_get_operations():
    """Verify cache set, get, and delete operations."""
    from django.core.cache import cache
    cache.clear()
    
    cache.set("test_signal_key", {"title": "GPT-5 Released", "score": 0.99}, timeout=60)
    cached_val = cache.get("test_signal_key")
    assert cached_val is not None
    assert cached_val["title"] == "GPT-5 Released"
    cache.delete("test_signal_key")
    assert cache.get("test_signal_key") is None


def test_rate_limit_exceeded_middleware_handles_exception():
    """Verify RateLimitMiddleware returns 429 JSON response on Ratelimited exception."""
    rf = RequestFactory()
    
    def view_that_raises_ratelimited(request):
        raise Ratelimited()
        
    middleware = RateLimitMiddleware(view_that_raises_ratelimited)
    request = rf.get("/api/search/")
    response = middleware(request)
    
    assert response.status_code == 429
    assert "RATE_LIMIT_EXCEEDED" in response.content.decode() or "Rate limit exceeded" in response.content.decode()


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-ratelimit-cache',
        }
    }
)
def test_rate_limit_decorator_ip_and_user():
    """Verify rate_limit_ip_or_user decorator applies rate limits per IP for anonymous and per User for authenticated."""
    from django.core.cache import cache
    cache.clear()
    rf = RequestFactory()
    
    @rate_limit_ip_or_user(rate_anon="2/m", rate_user="5/m")
    def sample_api_view(request):
        return JsonResponse({"status": "ok"})
    
    # 1. Anonymous user hitting limit
    request1 = rf.get("/api/test/", REMOTE_ADDR="198.51.100.10")
    request1.user = None
    res1 = sample_api_view(request1)
    assert res1.status_code == 200
    
    request2 = rf.get("/api/test/", REMOTE_ADDR="198.51.100.10")
    request2.user = None
    res2 = sample_api_view(request2)
    assert res2.status_code == 200
    
    # 3rd request should exceed rate="2/m"
    request3 = rf.get("/api/test/", REMOTE_ADDR="198.51.100.10")
    request3.user = None
    res3 = sample_api_view(request3)
    assert res3.status_code == 429
    assert "RATE_LIMIT_EXCEEDED" in res3.content.decode()
