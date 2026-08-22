import os
import sys
import math
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

from apps.knowledge_base.models import KnowledgeBaseNode, SignalType, EmbeddingStatus
from apps.knowledge_base.services.search_service import HybridSearchService, compute_rrf_score


def test_compute_rrf_score():
    """Verify Reciprocal Rank Fusion mathematical computation."""
    # Doc ranked #1 in both FTS and Vector (k=60)
    score_both_top = compute_rrf_score(fts_rank=1, vec_rank=1, k=60)
    expected_top = (1.0 / 61.0) + (1.0 / 61.0)
    assert math.isclose(score_both_top, expected_top, rel_tol=1e-5)
    
    # Doc ranked #1 in FTS only
    score_fts_only = compute_rrf_score(fts_rank=1, vec_rank=None, k=60)
    assert math.isclose(score_fts_only, 1.0 / 61.0, rel_tol=1e-5)
    
    # Blended match must outrank isolated match
    assert score_both_top > score_fts_only
    
    # Lower rank produces lower score
    score_lower = compute_rrf_score(fts_rank=5, vec_rank=10, k=60)
    assert score_lower < score_both_top


@pytest.mark.django_db
def test_hybrid_search_blended_ranking():
    """Verify HybridSearchService ranks multi-modal matches higher than single-modality matches."""
    # Clean test records
    KnowledgeBaseNode.objects.all().delete()
    
    # Target vector representing AI framework optimization
    query_vector = [0.1] * 384
    norm_q = math.sqrt(sum(x * x for x in query_vector))
    query_vector = [x / norm_q for x in query_vector]
    
    # Doc 1: Keyword "PyTorch" + highly aligned vector
    doc1 = KnowledgeBaseNode.objects.create(
        title="PyTorch 2.5 Released with FlashAttention Integration",
        content_raw="PyTorch 2.5 introduces kernel optimizations and accelerated training loops.",
        content_processed="PyTorch 2.5 includes native FP8 training.",
        source_url="https://pytorch.org/blog/pytorch-2-5",
        signal_type=SignalType.UPGRADE,
        embedding_status=EmbeddingStatus.COMPLETED,
        embedding_vector=query_vector  # Perfect cosine match
    )
    
    # Doc 2: Keyword "PyTorch" + orthogonal vector (low semantic match)
    ortho_vector = [-0.1] * 384
    norm_o = math.sqrt(sum(x * x for x in ortho_vector))
    ortho_vector = [x / norm_o for x in ortho_vector]
    
    doc2 = KnowledgeBaseNode.objects.create(
        title="PyTorch vs TensorFlow Historical Analysis",
        content_raw="An archive review of historical trends in 2018 deep learning frameworks.",
        content_processed="Historical analysis of PyTorch and TensorFlow 1.0.",
        source_url="https://example.com/history",
        signal_type=SignalType.GENERAL,
        embedding_status=EmbeddingStatus.COMPLETED,
        embedding_vector=ortho_vector
    )
    
    # Doc 3: Highly aligned vector + different keywords ("Deep learning framework tensor compiler")
    doc3 = KnowledgeBaseNode.objects.create(
        title="Deep Learning Tensor Compiler Breakthrough",
        content_raw="Accelerating matrix multiplication without PyTorch references.",
        content_processed="New compiler primitives for AI accelerators.",
        source_url="https://example.com/compiler",
        signal_type=SignalType.RESEARCH,
        embedding_status=EmbeddingStatus.COMPLETED,
        embedding_vector=query_vector
    )
    
    service = HybridSearchService()
    results = service.hybrid_search(
        query="PyTorch 2.5 acceleration",
        query_vector=query_vector,
        limit=5,
        k=60
    )
    
    assert len(results) >= 2
    # Doc 1 (matches both FTS and dense vector) must be top ranked
    top_result = results[0]
    assert top_result["id"] == doc1.id
    assert "PyTorch 2.5" in top_result["title"]
    assert top_result["rrf_score"] > 0.0


@pytest.mark.django_db
def test_hybrid_search_signal_type_filter():
    """Verify hybrid search respects signal taxonomy filter."""
    KnowledgeBaseNode.objects.all().delete()
    
    doc_research = KnowledgeBaseNode.objects.create(
        title="Scaling Laws for Reasoning Models",
        content_raw="Research paper analyzing test-time compute.",
        content_processed="Test time compute scaling analysis.",
        source_url="https://arxiv.org/abs/2410.9999",
        signal_type=SignalType.RESEARCH,
        embedding_status=EmbeddingStatus.COMPLETED,
        embedding_vector=[0.05] * 384
    )
    
    doc_funding = KnowledgeBaseNode.objects.create(
        title="AI Reasoning Startup Raises $100M",
        content_raw="Startup raises series B for reasoning models.",
        content_processed="Series B funding round announcement.",
        source_url="https://techcrunch.com/reasoning-funding",
        signal_type=SignalType.FUNDING,
        embedding_status=EmbeddingStatus.COMPLETED,
        embedding_vector=[0.05] * 384
    )
    
    service = HybridSearchService()
    results = service.hybrid_search(
        query="reasoning models",
        signal_type="RESEARCH",
        limit=5
    )
    
    assert len(results) == 1
    assert results[0]["id"] == doc_research.id
    assert results[0]["signal_type"] == "RESEARCH"
