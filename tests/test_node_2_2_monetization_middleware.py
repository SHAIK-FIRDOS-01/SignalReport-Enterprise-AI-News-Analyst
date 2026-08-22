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
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import AnonymousUser
from apps.accounts.models import CustomUser
from apps.accounts.monetization import MonetizationMiddleware, FREE_AI_CALLS_LIMIT


def dummy_ai_view(request):
    return JsonResponse({"status": "success", "data": "AI intelligence generated"})


def dummy_public_view(request):
    return JsonResponse({"status": "success", "data": "Public news articles"})


def test_monetization_unauthenticated_blocked_on_ai_endpoint():
    """Verify unauthenticated requests to AI-gated endpoints return 401 Unauthorized."""
    rf = RequestFactory()
    middleware = MonetizationMiddleware(dummy_ai_view)
    
    request = rf.post("/ask/", {"question": "What is groq?"})
    request.user = AnonymousUser()
    
    response = middleware(request)
    assert response.status_code == 401
    assert "Authentication required" in response.content.decode()


def test_monetization_free_tier_first_call():
    """Verify new user (0/2 calls used) is allowed and usage increments to 1."""
    rf = RequestFactory()
    middleware = MonetizationMiddleware(dummy_ai_view)
    
    user = CustomUser(id=201, email="free_user1@signalreport.ai", ai_calls_used=0, payment_method_active=False)
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr(user, "save", lambda **kw: None)
        request = rf.post("/ask/", {"question": "Explain RAG"})
        request.user = user
        
        response = middleware(request)
        assert response.status_code == 200
        assert user.ai_calls_used == 1


def test_monetization_free_tier_second_call():
    """Verify user on 2nd call (1/2 used) is allowed and usage increments to 2."""
    rf = RequestFactory()
    middleware = MonetizationMiddleware(dummy_ai_view)
    
    user = CustomUser(id=202, email="free_user2@signalreport.ai", ai_calls_used=1, payment_method_active=False)
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr(user, "save", lambda **kw: None)
        request = rf.post("/briefings/", {})
        request.user = user
        
        response = middleware(request)
        assert response.status_code == 200
        assert user.ai_calls_used == 2


def test_monetization_free_tier_hard_cap_blocked():
    """Verify user with 2/2 calls used is blocked with HTTP 402 Payment Required."""
    rf = RequestFactory()
    middleware = MonetizationMiddleware(dummy_ai_view)
    
    user = CustomUser(id=203, email="capped_user@signalreport.ai", ai_calls_used=2, payment_method_active=False)
    
    request = rf.post("/summarize/42/", {})
    request.user = user
    
    response = middleware(request)
    assert response.status_code == 402
    assert "PAYMENT_REQUIRED" in response.content.decode() or "limit reached" in response.content.decode().lower()


def test_monetization_premium_unlimited_bypass():
    """Verify premium user (payment_method_active=True) bypasses 2-call quota."""
    rf = RequestFactory()
    middleware = MonetizationMiddleware(dummy_ai_view)
    
    user = CustomUser(id=204, email="vip@signalreport.ai", ai_calls_used=50, payment_method_active=True)
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr(user, "save", lambda **kw: None)
        request = rf.post("/ask/", {"question": "Enterprise analysis"})
        request.user = user
        
        response = middleware(request)
        assert response.status_code == 200


def test_monetization_non_gated_endpoint_passthrough():
    """Verify public endpoints pass through without quota deductions."""
    rf = RequestFactory()
    middleware = MonetizationMiddleware(dummy_public_view)
    
    user = CustomUser(id=205, email="capped@signalreport.ai", ai_calls_used=2, payment_method_active=False)
    
    request = rf.get("/search/?q=python")
    request.user = user
    
    response = middleware(request)
    assert response.status_code == 200
    assert user.ai_calls_used == 2
