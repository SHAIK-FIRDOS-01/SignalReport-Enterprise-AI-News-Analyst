"""
Views for AI intelligence analysis.
Enforces IP-address and user-account ban cooldowns (default 4 hours) to prevent Groq API exhaustion.
"""

from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LLMUsageBan, LLMUsageLog
from .serializers import AnalyzeRequestSerializer
from .services.llm_service import analyze_article_content
from core.security import resolve_client_ip


class AnalyzeArticleView(APIView):
    """
    Direct in-context LLM analysis of a single news article with heuristic fallback.
    Allows up to N requests (default: 3) before enforcing an IP and user-account ban cooldown
    (default: 4 hours) to prevent Groq API quota exhaustion.
    Endpoints: POST /api/v1/news/analyze/, POST /api/v1/analyze/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        client_ip = resolve_client_ip(request)
        now = timezone.now()
        ban_hours = getattr(settings, "LLM_BAN_DURATION_HOURS", 4)
        max_requests = getattr(settings, "LLM_MAX_REQUESTS_BEFORE_BAN", 3)

        # 1. Threat-boundary & Quota enforcement: Check active ban on caller IP or authenticated User
        ban_filter = Q(ip_address=client_ip, banned_until__gt=now)
        if request.user and request.user.is_authenticated:
            ban_filter |= Q(user=request.user, banned_until__gt=now)

        active_ban = LLMUsageBan.objects.filter(ban_filter).order_by("-banned_until").first()
        if active_ban:
            remaining_seconds = max(1, int((active_ban.banned_until - now).total_seconds()))
            remaining_hours = round(remaining_seconds / 3600, 1)
            remaining_minutes = max(1, int(remaining_seconds / 60))
            ban_expires_str = active_ban.banned_until.strftime("%Y-%m-%d %H:%M:%S UTC")

            response = Response(
                {
                    "detail": (
                        f"LLM access restricted: You have reached the limit of {max_requests} AI analyses. "
                        f"Your IP address ({client_ip}) and account are temporarily restricted for the next "
                        f"{remaining_hours}h ({remaining_minutes}m) due to API quota limits. "
                        f"Ban expires at {ban_expires_str}."
                    ),
                    "banned_until": active_ban.banned_until.isoformat(),
                    "retry_after": remaining_seconds,
                    "code": "LLM_RATE_LIMITED",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(remaining_seconds)
            return response

        # 2. Check recent request count within active window
        window_start = now - timedelta(hours=ban_hours)
        log_filter = Q(ip_address=client_ip, created_at__gte=window_start)
        if request.user and request.user.is_authenticated:
            log_filter |= Q(user=request.user, created_at__gte=window_start)

        recent_requests_count = LLMUsageLog.objects.filter(log_filter).count()

        if recent_requests_count >= max_requests:
            banned_until = now + timedelta(hours=ban_hours)
            LLMUsageBan.objects.create(
                ip_address=client_ip,
                user=request.user if (request.user and request.user.is_authenticated) else None,
                banned_until=banned_until,
                reason=f"LLM quota limit of {max_requests} requests reached",
            )
            retry_seconds = int(ban_hours * 3600)
            response = Response(
                {
                    "detail": (
                        f"LLM access restricted: You have used all {max_requests} allowed AI analyses. "
                        f"Your IP address ({client_ip}) and account are restricted for the next {ban_hours} hours."
                    ),
                    "banned_until": banned_until.isoformat(),
                    "retry_after": retry_seconds,
                    "code": "LLM_RATE_LIMITED",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(retry_seconds)
            return response

        # 3. Validate payload
        serializer = AnalyzeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        result = analyze_article_content(
            title=data["title"],
            description=data.get("description"),
            content=data.get("content"),
            source=data.get("source_name"),
            category=data.get("category"),
        )

        # 4. Log this successful analysis request
        LLMUsageLog.objects.create(
            ip_address=client_ip,
            user=request.user if (request.user and request.user.is_authenticated) else None,
        )

        current_usage = recent_requests_count + 1
        remaining_requests = max(0, max_requests - current_usage)

        # 5. If this was the Nth allowed request (3rd), trigger the cooldown ban immediately
        if current_usage >= max_requests:
            banned_until = now + timedelta(hours=ban_hours)
            LLMUsageBan.objects.create(
                ip_address=client_ip,
                user=request.user if (request.user and request.user.is_authenticated) else None,
                banned_until=banned_until,
                reason=f"LLM quota limit of {max_requests} requests reached. Cooldown for {ban_hours}h",
            )
            result["banned_until"] = banned_until.isoformat()

        result["requests_used"] = current_usage
        result["requests_remaining"] = remaining_requests
        result["quota_limit"] = max_requests

        return Response(result, status=status.HTTP_200_OK)
