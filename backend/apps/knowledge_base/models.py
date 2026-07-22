from django.db import models
from django.utils.translation import gettext_lazy as _
from pgvector.django import VectorField
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class EmbeddingStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    PROCESSING = 'PROCESSING', _('Processing')
    COMPLETED = 'COMPLETED', _('Completed')
    FAILED = 'FAILED', _('Failed')

class KnowledgeBaseNode(models.Model):
    """
    RAG Foundation Model representing an ingested and processed news article.
    """
    title = models.CharField(max_length=500)
    source_url = models.URLField(max_length=500, unique=True)
    published_at = models.DateTimeField(null=True, blank=True)
    category = models.CharField(max_length=100, default='General', db_index=True)
    geography = models.CharField(max_length=50, default='International', db_index=True)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    
    # Content Fields
    content_raw = models.TextField(help_text=_("Original unedited snippet from the source"))
    full_text_scraped = models.TextField(blank=True, null=True, help_text=_("Complete article body extracted by the scraper"))
    content_processed = models.TextField(blank=True, null=True, help_text=_("Cleaned and AI-enhanced summary/analysis"))
    
    # RAG specific fields
    embedding_status = models.CharField(
        max_length=20,
        choices=EmbeddingStatus.choices,
        default=EmbeddingStatus.PENDING
    )
    
    # Vector Field - using pgvector
    embedding_vector = VectorField(
        dimensions=5, # Using 5 to match the current Groq prompt mock, normally 1536 for OpenAI etc
        blank=True, 
        null=True, 
        help_text=_("Vector representation for RAG using pgvector")
    )
    
    # Full-Text Search Field
    search_vector = SearchVectorField(null=True, blank=True)
    
    # Quality & Reliability
    source_credibility_score = models.FloatField(
        default=0.0, 
        help_text=_("Calculated credibility score from NLP/AI processing")
    )
    
    # Sentiment & Entity Tracking (For Trend Analytics)
    sentiment_score = models.FloatField(default=0.0, help_text=_("NLP Sentiment Score from -1.0 to 1.0"))
    entities = models.JSONField(default=list, blank=True, help_text=_("Extracted entities (organizations, locations, etc.)"))
    
    # Auditing / Fallback
    fail_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kb_node'
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['embedding_status']),
            models.Index(fields=['published_at']),
            GinIndex(fields=['search_vector']),
        ]

    def __str__(self):
        return f"[{self.embedding_status}] {self.title[:50]}"


