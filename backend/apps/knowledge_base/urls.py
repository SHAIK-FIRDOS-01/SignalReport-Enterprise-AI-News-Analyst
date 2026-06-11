from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('summarize/<int:node_id>/', views.SummarizeView.as_view(), name='summarize'),
    path('ingest/', views.IngestView.as_view(), name='ingest'),
    path('glossary/', views.GlossaryView.as_view(), name='glossary'),
    path('ask/', views.AskQuestionView.as_view(), name='ask'),
    path('briefings/', views.BriefingsView.as_view(), name='briefings'),
    path('api/top-headlines', views.GNewsHeadlinesView.as_view(), name='api_headlines'),
    path('api/search', views.GNewsSearchView.as_view(), name='api_search'),
]
