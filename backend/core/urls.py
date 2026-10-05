"""
Root URL configuration for SignalReport Django project.
Mounts authentication and feed apps under /api/v1/ and root fallback prefixes.
"""

from django.contrib import admin
from django.urls import path, include
from apps.feed.views import HealthCheckView

urlpatterns = [
    # Admin interface
    path("admin/", admin.site.urls),

    # Health check endpoints
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("health", HealthCheckView.as_view(), name="health-check-no-slash"),

    # Version 1 API Routing (Primary)
    path("api/v1/auth/", include("apps.authentication.urls", namespace="api-v1-auth")),
    path("api/v1/", include("apps.feed.urls", namespace="api-v1-feed")),
    path("api/v1/", include("apps.intelligence.urls", namespace="api-v1-intelligence")),

    # Root Fallbacks (Matching FastAPI dual-mount behavior)
    path("auth/", include("apps.authentication.urls", namespace="root-auth")),
    path("", include("apps.feed.urls", namespace="root-feed")),
    path("", include("apps.intelligence.urls", namespace="root-intelligence")),
]
