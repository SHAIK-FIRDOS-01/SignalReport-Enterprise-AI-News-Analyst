import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from asgiref.sync import async_to_sync
from django_ratelimit.decorators import ratelimit

from .models import KnowledgeBaseNode
from .tasks import process_article_pipeline, trigger_news_ingestion
from .tasks import process_article_pipeline, trigger_news_ingestion
from apps.accounts.utils import require_jwt, role_required

@method_decorator(require_jwt, name='dispatch')
# @method_decorator(cache_page(60 * 5), name='dispatch') # Cache for 5 mins
@method_decorator(vary_on_headers('Authorization'), name='dispatch')
class DashboardView(View):
    """ Main dashboard API endpoint. """
    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta
        import asyncio
        import threading
        
        latest_node = KnowledgeBaseNode.objects.order_by('-created_at').first()
        is_fresh_install = not latest_node
        needs_ingestion = False
        
        if is_fresh_install:
            needs_ingestion = True
        elif latest_node.created_at < timezone.now() - timedelta(hours=1):
            needs_ingestion = True

        if needs_ingestion:
            from .tasks import fast_ingest_and_save, background_scrape_all_pending
            
            def run_ingestion_and_scraping():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(fast_ingest_and_save(is_historical=is_fresh_install))
                loop.run_until_complete(background_scrape_all_pending())
                loop.close()
                
            if is_fresh_install:
                # Synchronous on fresh install so first load is not empty
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(fast_ingest_and_save(is_historical=True))
                loop.close()
                
                # Defer scraping in background
                def run_background_scraping():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(background_scrape_all_pending())
                    loop.close()
                thread = threading.Thread(target=run_background_scraping)
                thread.daemon = True
                thread.start()
            else:
                # Run ingestion and scraping entirely in background to avoid blocking the user
                thread = threading.Thread(target=run_ingestion_and_scraping)
                thread.daemon = True
                thread.start()

        nodes = KnowledgeBaseNode.objects.all().order_by('-published_at')
        
        # Category filter
        category = request.GET.get('category', 'All')
        if category != 'All':
            nodes = nodes.filter(category__iexact=category)
            
        # Geography filter
        geography = request.GET.get('geography', 'All')
        if geography != 'All':
            nodes = nodes.filter(geography__iexact=geography)
            
        data = [{
            'id': node.id,
            'title': node.title,
            'category': node.category,
            'geography': node.geography,
            'content_raw': node.content_raw,
            'full_text_scraped': node.full_text_scraped,
            'content_processed': node.content_processed,
            'embedding_status': node.embedding_status,
            'source_credibility_score': node.source_credibility_score,
            'published_at': node.published_at.isoformat() if node.published_at else None,
            'source_url': node.source_url,
            'image_url': node.image_url
        } for node in nodes[:50]]
        return JsonResponse({'nodes': data})

@method_decorator(require_jwt, name='dispatch')
class SearchView(View):
    """ Global search API endpoint using Hybrid Search. """
    def get(self, request):
        from .search import hybrid_search
        query = request.GET.get('q', '')
        
        # In a real setup, we would embed the query here.
        # Mocking query vector for now to match dimensions=5
        mock_query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        nodes = hybrid_search(query, mock_query_vector, limit=10)
        
        data = [{
            'id': node.id,
            'title': node.title,
            'content_raw': node.content_raw,
            'content_processed': node.content_processed,
            'embedding_status': node.embedding_status,
        } for node in nodes]
        return JsonResponse({'nodes': data})

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_jwt, name='dispatch')
@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class SummarizeView(View):
    """ API endpoint to trigger summarization. """
    def post(self, request, node_id):
        try:
            node = get_object_or_404(KnowledgeBaseNode, id=node_id)
            async_to_sync(process_article_pipeline)(node.id)
            node.refresh_from_db()
            
            return JsonResponse({
                'status': 'success',
                'node': {
                    'id': node.id,
                    'content_processed': node.content_processed,
                    'embedding_status': node.embedding_status
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_jwt, name='dispatch')
class IngestView(View):
    """ API endpoint to manually trigger a news fetch. """
    def post(self, request):
        try:
            async_to_sync(trigger_news_ingestion)("AI technology breakthrough")
            return JsonResponse({'status': 'success', 'message': 'Ingestion started'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Ingestion failed'}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_jwt, name='dispatch')
@method_decorator(role_required(['ANALYST', 'ADMIN']), name='dispatch')
@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='dispatch')
class GlossaryView(View):
    """ API endpoint to define a term based on the article's context. """
    def post(self, request):
        from services.ai_service import AIService
        try:
            data = json.loads(request.body)
            term = data.get('term')
            node_id = data.get('node_id')
            
            node = get_object_or_404(KnowledgeBaseNode, id=node_id)
            ai_service = AIService()
            context = node.full_text_scraped or node.content_raw
            
            definition = async_to_sync(ai_service.explain_term)(term, context)
            return JsonResponse({'status': 'success', 'definition': definition})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_jwt, name='dispatch')
@method_decorator(role_required(['ANALYST', 'ADMIN']), name='dispatch')
@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='dispatch')
class AskQuestionView(View):
    """ API endpoint to answer a question based on the article's context. """
    def post(self, request):
        from services.ai_service import AIService
        try:
            data = json.loads(request.body)
            question = data.get('question')
            node_id = data.get('node_id')
            
            node = get_object_or_404(KnowledgeBaseNode, id=node_id)
            ai_service = AIService()
            context = node.full_text_scraped or node.content_processed or node.content_raw
            
            answer = async_to_sync(ai_service.answer_question)(question, context, node.source_url)
            return JsonResponse({'status': 'success', 'answer': answer})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

class GNewsHeadlinesView(View):
    """
    Proxy endpoint for the GNews top-headlines service.
    """
    def get(self, request):
        import httpx
        from django.conf import settings
        from django.utils import timezone
        
        base_url = getattr(settings, 'MICROSERVICE_URL', 'http://localhost:8001')
        url = f"{base_url.rstrip('/')}/news/headlines"
        
        category = request.GET.get('category', 'general')
        q = request.GET.get('q', None)
        lang = request.GET.get('lang', None)
        country = request.GET.get('country', None)
        max_val = int(request.GET.get('max', 10))
        from_date = request.GET.get('from', None)
        to_date = request.GET.get('to', None)
        nullable = request.GET.get('nullable', None)
        
        payload = {
            "category": category,
            "max_results": max_val
        }
        if q:
            payload["query"] = q
        if lang:
            payload["lang"] = lang
        if country:
            payload["country"] = country
        if from_date:
            payload["from_date"] = from_date
        if to_date:
            payload["to_date"] = to_date
        if nullable:
            payload["nullable"] = nullable

        requested_url = f"https://gnews.io/api/v4/top-headlines?category={category}&max={max_val}"
        if q: requested_url += f"&q={q}"
        if lang: requested_url += f"&lang={lang}"
        if country: requested_url += f"&country={country}"
        if from_date: requested_url += f"&from={from_date}"
        if to_date: requested_url += f"&to={to_date}"
        if nullable: requested_url += f"&nullable={nullable}"

        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                articles = data.get("articles", [])
                
                return JsonResponse({
                    "success": True,
                    "articles": articles,
                    "totalArticles": len(articles),
                    "debug": {
                        "requestedUrl": requested_url,
                        "status": response.status_code,
                        "statusText": "OK",
                        "timestamp": timezone.now().isoformat()
                    },
                    "raw": {
                        "articles": articles
                    }
                })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": f"Microservice error: {str(e)}",
                "debug": {
                    "requestedUrl": requested_url,
                    "status": 500,
                    "statusText": "Internal Server Error",
                    "timestamp": timezone.now().isoformat()
                }
            }, status=500)

class GNewsSearchView(View):
    """
    Proxy endpoint for the GNews search service.
    """
    def get(self, request):
        import httpx
        from django.conf import settings
        from django.utils import timezone
        
        base_url = getattr(settings, 'MICROSERVICE_URL', 'http://localhost:8001')
        url = f"{base_url.rstrip('/')}/news/fetch"
        
        q = request.GET.get('q', 'AI advancements')
        lang = request.GET.get('lang', None)
        country = request.GET.get('country', None)
        max_val = int(request.GET.get('max', 10))
        from_date = request.GET.get('from', None)
        to_date = request.GET.get('to', None)
        sortby = request.GET.get('sortby', 'publishedAt')
        nullable = request.GET.get('nullable', None)
        
        payload = {
            "query": q,
            "max_results": max_val,
            "sortby": sortby
        }
        if lang:
            payload["lang"] = lang
        if country:
            payload["country"] = country
        if from_date:
            payload["from_date"] = from_date
        if to_date:
            payload["to_date"] = to_date
        if nullable:
            payload["nullable"] = nullable

        requested_url = f"https://gnews.io/api/v4/search?q={q}&max={max_val}&sortby={sortby}"
        if lang: requested_url += f"&lang={lang}"
        if country: requested_url += f"&country={country}"
        if from_date: requested_url += f"&from={from_date}"
        if to_date: requested_url += f"&to={to_date}"
        if nullable: requested_url += f"&nullable={nullable}"

        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                articles = data.get("articles", [])
                
                return JsonResponse({
                    "success": True,
                    "articles": articles,
                    "totalArticles": len(articles),
                    "debug": {
                        "requestedUrl": requested_url,
                        "status": response.status_code,
                        "statusText": "OK",
                        "timestamp": timezone.now().isoformat()
                    },
                    "raw": {
                        "articles": articles
                    }
                })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": f"Microservice error: {str(e)}",
                "debug": {
                    "requestedUrl": requested_url,
                    "status": 500,
                    "statusText": "Internal Server Error",
                    "timestamp": timezone.now().isoformat()
                }
            }, status=500)



@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_jwt, name='dispatch')
@method_decorator(role_required(['ANALYST', 'ADMIN']), name='dispatch')
class BriefingsView(View):
    """ Synthesizes multi-article briefings by calling FastAPI Groq endpoint. """
    def post(self, request):
        from services.ai_service import AIService
        try:
            data = json.loads(request.body)
            node_ids = data.get('node_ids', [])
            nodes = KnowledgeBaseNode.objects.filter(id__in=node_ids)
            
            articles = []
            for node in nodes:
                articles.append({
                    "title": node.title,
                    "content": node.content_processed or node.content_raw,
                    "source_url": node.source_url
                })
                
            if not articles:
                return JsonResponse({'status': 'error', 'message': 'No articles selected.'}, status=400)
                
            ai_service = AIService()
            briefing = async_to_sync(ai_service.generate_briefing)(articles)
            return JsonResponse({'status': 'success', 'briefing': briefing})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


