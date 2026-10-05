"""
Intelligence URL Routing for AI analysis endpoints.
"""

from django.urls import path
from .views import AnalyzeArticleView

app_name = "intelligence"

urlpatterns = [
    path("news/analyze/", AnalyzeArticleView.as_view(), name="news-analyze"),
    path("news/analyze", AnalyzeArticleView.as_view(), name="news-analyze-noslash"),
    path("analyze/", AnalyzeArticleView.as_view(), name="analyze"),
    path("analyze", AnalyzeArticleView.as_view(), name="analyze-noslash"),
]
