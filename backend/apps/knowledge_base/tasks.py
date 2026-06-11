import asyncio
import logging
from asgiref.sync import sync_to_async
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

from .models import KnowledgeBaseNode, EmbeddingStatus
from services.news_ingestion import NewsIngestionService
from services.nlp_processing import NLPProcessingService
from services.ai_service import AIService
from services.scraper_service import ContentScraperService

logger = logging.getLogger(__name__)

INGESTION_LOCK_KEY = "news_ingestion_lock"
INGESTION_LOCK_TIMEOUT = 600  # 10 minutes

async def fast_ingest_and_save(is_historical: bool = False):
    """
    Fetches news from GNews API and saves to database.
    """
    # 1. Acquire Distributed Lock
    lock_acquired = cache.add(INGESTION_LOCK_KEY, "true", INGESTION_LOCK_TIMEOUT)
    if not lock_acquired:
        logger.warning("Ingestion already in progress. Skipping fast fetch.")
        return 0

    try:
        logger.info(f"Starting {'Historical ' if is_historical else 'Latest '}Fast Ingestion...")
        
        regions = [
            {"name": "India", "country": "in"},
            {"name": "International", "country": "us"}
        ]
        
        categories = {
            "General": "general",
            "Business": "business",
            "Technology": "technology",
            "Science": "science",
            "Sports": "sports"
        }

        ingestion_service = NewsIngestionService()
        total_created = 0

        async def fetch_and_save(region, label, gnews_cat):
            try:
                articles = await ingestion_service.fetch_top_headlines(
                    category=gnews_cat,
                    lang="en",
                    country=region["country"],
                    max_results=15 if is_historical else 10
                )
                
                created_in_cat = 0
                for art in articles:
                    node, created = await sync_to_async(KnowledgeBaseNode.objects.get_or_create)(
                        source_url=art['url'],
                        defaults={
                            'title': art['title'],
                            'content_raw': art.get('description') or art.get('content') or '',
                            'published_at': art.get('publishedAt', timezone.now()),
                            'category': label,
                            'geography': region['name'],
                            'image_url': art.get('image')
                        }
                    )
                    if created:
                        created_in_cat += 1
                return created_in_cat
            except Exception as ex:
                logger.error(f"Error fetching region {region['name']} cat {label}: {str(ex)}")
                return 0

        # Fetch standard GNews feeds
        tasks = []
        for region in regions:
            for label, gnews_cat in categories.items():
                tasks.append(fetch_and_save(region, label, gnews_cat))
                
        results = await asyncio.gather(*tasks)
        total_created += sum(results)

        logger.info(f"Fast Ingestion completed. {total_created} new articles saved.")
        return total_created

    except Exception as e:
        logger.error(f"Fast ingestion failed: {str(e)}")
        return 0
    finally:
        cache.delete(INGESTION_LOCK_KEY)

async def background_scrape_all_pending():
    """
    Background worker that loops through unscraped articles and extracts their full text.
    """
    try:
        from django.db.models import Q
        # Retrieve all nodes missing scraped text
        nodes = await sync_to_async(list)(
            KnowledgeBaseNode.objects.filter(Q(full_text_scraped__isnull=True) | Q(full_text_scraped=''))
        )
        
        if not nodes:
            return
            
        logger.info(f"Starting background scraping for {len(nodes)} articles...")
        scraper_service = ContentScraperService()
        total_scraped = 0
        
        for node in nodes:
            try:
                full_text = await scraper_service.scrape_full_content(node.source_url)
                if full_text:
                    node.full_text_scraped = full_text
                    await sync_to_async(node.save)(update_fields=['full_text_scraped'])
                    total_scraped += 1
            except Exception as e:
                logger.error(f"Failed background scraping for {node.source_url}: {str(e)}")
                
        logger.info(f"Background scraping completed. {total_scraped} articles enriched.")
    except Exception as e:
        logger.error(f"Background scraping worker failed: {str(e)}")

async def process_article_pipeline(article_id: int):
    """
    Enrichment pipeline that uses full scraped text if available, extracting sentiment and entities.
    """
    try:
        node = await sync_to_async(KnowledgeBaseNode.objects.get)(id=article_id)
        
        if node.embedding_status == EmbeddingStatus.COMPLETED and node.content_processed:
            logger.info(f"Article {article_id} already processed. Skipping.")
            return
 
        node.embedding_status = EmbeddingStatus.PROCESSING
        await sync_to_async(node.save)(update_fields=['embedding_status'])

        logger.info(f"Starting pipeline for article: {node.title}")

        # Use full text if we have it, otherwise fallback to GNews snippet
        analysis_content = node.full_text_scraped or node.content_raw

        # 2. NLP Processing
        nlp_service = NLPProcessingService()
        nlp_result = await nlp_service.process_content(analysis_content)
        
        # 3. AI Service (Uses full text for deep analysis)
        ai_service = AIService()
        ai_result = await ai_service.enhance_and_vectorize(
            content=analysis_content, 
            nlp_context=nlp_result
        )

        # 4. Update Node
        enhanced_content = ai_result.get('enhanced_content', node.content_raw)
        node.content_processed = enhanced_content
        node.embedding_vector = ai_result.get('vector')
        node.source_credibility_score = ai_result.get('credibility_score', 0.5)
        
        # Save Sentiment & Entities
        node.sentiment_score = nlp_result.get('sentiment', 0.0)
        node.entities = nlp_result.get('entities', [])
        
        if enhanced_content.startswith("FALLBACK_MODE"):
            node.embedding_status = EmbeddingStatus.FAILED
            node.fail_reason = "AI Processing Fallback: Quota exceeded or API error."
        else:
            node.embedding_status = EmbeddingStatus.COMPLETED
            
        await sync_to_async(node.save)()
        logger.info(f"Successfully processed article: {node.title}")

    except KnowledgeBaseNode.DoesNotExist:
        logger.error(f"Article with id {article_id} not found.")
    except Exception as e:
        logger.error(f"Pipeline failed for article {article_id}: {str(e)}")
        if 'node' in locals():
            node.embedding_status = EmbeddingStatus.FAILED
            node.fail_reason = str(e)
            await sync_to_async(node.save)(update_fields=['embedding_status', 'fail_reason'])

async def full_system_ingestion(is_historical: bool = False):
    """
    Legacy method kept for backwards compatibility.
    """
    await fast_ingest_and_save(is_historical)
    await background_scrape_all_pending()

async def trigger_news_ingestion(query: str = "AI advancements"):
    """
    Legacy background task for backward compatibility.
    """
    return await fast_ingest_and_save(is_historical=False)
