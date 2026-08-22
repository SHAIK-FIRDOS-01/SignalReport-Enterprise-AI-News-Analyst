import os
import sys
from pathlib import Path
import pytest

# Ensure backend path is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from apps.knowledge_base.models import KnowledgeBaseNode, EmbeddingStatus
from pgvector.django import VectorField
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


def test_custom_user_monetization_fields():
    """Verify CustomUser has ai_calls_used and payment_method_active fields with correct defaults."""
    User = get_user_model()
    
    # Check field existence on model
    ai_calls_field = User._meta.get_field('ai_calls_used')
    payment_field = User._meta.get_field('payment_method_active')
    
    assert ai_calls_field is not None, "CustomUser must have ai_calls_used field"
    assert ai_calls_field.default == 0, "ai_calls_used must default to 0"
    
    assert payment_field is not None, "CustomUser must have payment_method_active field"
    assert payment_field.default is False, "payment_method_active must default to False"
    
    # Verify instantiation
    user = User(email="test@signalreport.ai")
    assert user.ai_calls_used == 0
    assert user.payment_method_active is False


def test_kb_node_schema_and_vector_dimension():
    """Verify KnowledgeBaseNode has 384D embedding_vector, signal_type, tech_domain, metadata_json, and GIN index."""
    # Check table name
    assert KnowledgeBaseNode._meta.db_table == 'kb_node'
    
    # Check embedding vector dimensions
    embedding_field = KnowledgeBaseNode._meta.get_field('embedding_vector')
    assert isinstance(embedding_field, VectorField), "embedding_vector must be a VectorField"
    assert embedding_field.dimensions == 384, "embedding_vector dimensions must be 384 for fastembed/bge-small-en-v1.5"
    
    # Check search vector and GIN index
    search_vector_field = KnowledgeBaseNode._meta.get_field('search_vector')
    assert isinstance(search_vector_field, SearchVectorField), "search_vector must be a SearchVectorField"
    
    gin_indexes = [idx for idx in KnowledgeBaseNode._meta.indexes if isinstance(idx, GinIndex)]
    assert len(gin_indexes) >= 1, "KnowledgeBaseNode must have at least one GinIndex on search_vector"
    assert 'search_vector' in gin_indexes[0].fields
    
    # Check taxonomy and metadata fields
    signal_type_field = KnowledgeBaseNode._meta.get_field('signal_type')
    assert signal_type_field.db_index is True, "signal_type must be indexed"
    
    tech_domain_field = KnowledgeBaseNode._meta.get_field('tech_domain')
    assert tech_domain_field.db_index is True, "tech_domain must be indexed"
    
    metadata_json_field = KnowledgeBaseNode._meta.get_field('metadata_json')
    assert metadata_json_field is not None, "metadata_json must be present"
