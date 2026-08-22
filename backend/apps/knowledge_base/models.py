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


class SignalType(models.TextChoices):
    LAUNCH = 'LAUNCH', _('Product/Model Launch')
    FUNDING = 'FUNDING', _('Startup Funding/M&A')
    RESEARCH = 'RESEARCH', _('Research Paper Breakthrough')
    UPGRADE = 'UPGRADE', _('Major Release/Upgrade')
    BUZZ = 'BUZZ', _('Viral Tech Discussion')
    GENERAL = 'GENERAL', _('General Tech Intelligence')


class KnowledgeBaseNode(models.Model):
    """
    RAG Foundation Model representing an ingested, analyzed, vectorized tech signal.
    Stored in the PostgreSQL 17 kb_node table with 384D pgvector embeddings.
    """
    title = models.CharField(max_length=500)
    source_url = models.URLField(max_length=500, unique=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Signal Taxonomy & Domain Classification
    signal_type = models.CharField(
        max_length=50,
        choices=SignalType.choices,
        default=SignalType.GENERAL,
        db_index=True,
        help_text=_("Categorized tech signal type (LAUNCH, FUNDING, RESEARCH, UPGRADE, BUZZ)")
    )
    tech_domain = models.CharField(
        max_length=100,
        default='General',
        db_index=True,
        help_text=_("Technology domain (e.g., AI/ML, Cloud, Security, Systems)")
    )
    category = models.CharField(max_length=100, default='General', db_index=True)
    geography = models.CharField(max_length=50, default='International', db_index=True)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    
    # Content Fields
    content_raw = models.TextField(blank=True, default='', help_text=_("Original unedited snippet from the source"))
    full_text_scraped = models.TextField(blank=True, null=True, help_text=_("Complete cleaned article body extracted in Markdown"))
    content_processed = models.TextField(blank=True, null=True, help_text=_("Cleaned and AI-enhanced summary/analysis"))
    
    # Structured Intelligence Metadata (Amounts, arXiv IDs, Benchmark Scores, etc.)
    metadata_json = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Structured funding amounts, arXiv IDs, benchmark scores, GitHub release tags")
    )
    
    # RAG Status & pgvector 384D Embedding Vector
    embedding_status = models.CharField(
        max_length=20,
        choices=EmbeddingStatus.choices,
        default=EmbeddingStatus.PENDING,
        db_index=True
    )
    embedding_vector = VectorField(
        dimensions=384,
        blank=True,
        null=True,
        help_text=_("384-dimension vector embedding (BAAI/bge-small-en-v1.5 via fastembed)")
    )
    
    # PostgreSQL Full-Text Search Vector
    search_vector = SearchVectorField(null=True, blank=True)
    
    # Quality & Reliability Metrics
    source_credibility_score = models.FloatField(
        default=0.0,
        help_text=_("Calculated credibility score from NLP/AI processing")
    )
    sentiment_score = models.FloatField(default=0.0, help_text=_("NLP Sentiment Score from -1.0 to 1.0"))
    entities = models.JSONField(default=list, blank=True, help_text=_("Extracted entities (organizations, authors, tools)"))
    
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
            models.Index(fields=['signal_type']),
            models.Index(fields=['tech_domain']),
            GinIndex(fields=['search_vector']),
        ]

    def __str__(self):
        return f"[{self.signal_type}][{self.embedding_status}] {self.title[:50]}"
