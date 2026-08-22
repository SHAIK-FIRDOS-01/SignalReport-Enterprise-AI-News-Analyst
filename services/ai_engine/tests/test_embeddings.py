import os
import sys
import math
from pathlib import Path
import pytest

root_dir = Path(__file__).resolve().parent.parent.parent.parent
ai_engine_dir = root_dir / "services" / "ai_engine"

for p in [str(root_dir), str(ai_engine_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from services.ai_engine.vector_service import VectorEmbeddingService


def test_generate_384d_embedding_vector():
    """Verify VectorEmbeddingService generates 384-dim normalized dense vectors using BAAI/bge-small-en-v1.5."""
    service = VectorEmbeddingService()
    text = "Meta AI releases Llama 3.3 70B open weights model with 128k context."
    
    vec = service.generate_embedding(text)
    
    assert isinstance(vec, list)
    assert len(vec) == 384
    assert all(isinstance(x, float) for x in vec)
    
    # Verify L2 norm normalization: sum(x^2)^0.5 ~= 1.0
    l2_norm = math.sqrt(sum(x * x for x in vec))
    assert math.isclose(l2_norm, 1.0, rel_tol=1e-2), f"L2 norm {l2_norm} not normalized to 1.0"


def test_generate_batch_embeddings():
    """Verify batch vector embedding generation returns expected shape."""
    service = VectorEmbeddingService()
    texts = [
        "OpenAI announces o3 reasoning model.",
        "Anthropic releases Claude 3.5 Sonnet upgrade."
    ]
    
    vectors = service.generate_embeddings_batch(texts)
    
    assert len(vectors) == 2
    for vec in vectors:
        assert len(vec) == 384
        l2_norm = math.sqrt(sum(x * x for x in vec))
        assert math.isclose(l2_norm, 1.0, rel_tol=1e-2)


def test_empty_string_handling():
    """Verify empty or whitespace strings return zero or normalized 384D fallback."""
    service = VectorEmbeddingService()
    vec = service.generate_embedding("")
    assert len(vec) == 384
    assert all(isinstance(x, float) for x in vec)
