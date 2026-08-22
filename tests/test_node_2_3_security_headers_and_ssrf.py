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

from django.test import RequestFactory
from django.http import HttpResponse
from apps.accounts.middleware import SecurityMiddleware
from apps.accounts.models import CustomUser
from core.security.anti_ssrf import (
    validate_url_anti_ssrf,
    is_safe_url,
    SSRFValidationError,
)


def test_security_headers_middleware():
    """Verify SecurityMiddleware injects strict CSP, X-Content-Type-Options, and Referrer-Policy."""
    rf = RequestFactory()
    middleware = SecurityMiddleware(lambda req: HttpResponse("Secure Response"))
    
    request = rf.get("/api/health/")
    response = middleware(request)
    
    # 1. CSP Header
    assert 'Content-Security-Policy' in response
    csp = response['Content-Security-Policy']
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    
    # 2. X-Content-Type-Options
    assert response.get('X-Content-Type-Options') == 'nosniff'
    
    # 3. Referrer-Policy & Permissions-Policy
    assert response.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert 'geolocation=()' in response.get('Permissions-Policy', '')


def test_security_headers_authenticated_cache_control():
    """Verify authenticated requests receive no-store Zero-Trust Cache-Control."""
    rf = RequestFactory()
    middleware = SecurityMiddleware(lambda req: HttpResponse("Secret User Data"))
    
    request = rf.get("/auth/me/")
    user = CustomUser(id=99, email="sec_user@signalreport.ai")
    request.user = user
    
    response = middleware(request)
    assert response.get('Cache-Control') == 'no-store, no-cache, must-revalidate, max-age=0'
    assert response.get('Pragma') == 'no-cache'


def test_anti_ssrf_allows_safe_public_urls():
    """Verify legitimate public HTTP/HTTPS URLs pass Anti-SSRF validation."""
    safe_urls = [
        "https://news.ycombinator.com",
        "https://arxiv.org/abs/2401.00001",
        "https://github.com/django/django/releases",
        "http://example.com/article",
    ]
    for url in safe_urls:
        assert is_safe_url(url) is True
        validated = validate_url_anti_ssrf(url)
        assert validated == url


def test_anti_ssrf_blocks_private_and_loopback_ips():
    """Verify Anti-SSRF strictly blocks loopback, private ranges, and cloud metadata IPs."""
    dangerous_urls = [
        "http://localhost:8000/internal",
        "http://127.0.0.1:8000/admin",
        "http://127.0.0.2/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1:8080/metrics",
        "http://192.168.1.1/router",
        "http://172.16.0.1/",
        "http://0.0.0.0:5000",
        "http://[::1]/",
        "file:///etc/passwd",
        "ftp://ftp.example.com",
        "gopher://127.0.0.1:70",
    ]
    for url in dangerous_urls:
        assert is_safe_url(url) is False, f"URL should have been marked unsafe: {url}"
        with pytest.raises(SSRFValidationError):
            validate_url_anti_ssrf(url)
