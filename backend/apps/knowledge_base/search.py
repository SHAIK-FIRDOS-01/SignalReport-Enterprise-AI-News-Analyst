from django.db.models import F
from django.contrib.postgres.search import SearchQuery, SearchRank
from pgvector.django import L2Distance
from .models import KnowledgeBaseNode

def hybrid_search(query: str, query_vector: list, limit: int = 10, rrf_k: int = 60):
    """
    Performs Hybrid Search using Full-Text Search (FTS) and Vector Similarity.
    Combines results using Reciprocal Rank Fusion (RRF).
    """
    # 1. Full-Text Search (Keyword Match)
    search_query = SearchQuery(query)
    fts_results = (
        KnowledgeBaseNode.objects
        .filter(search_vector=search_query)
        .annotate(rank=SearchRank(F('search_vector'), search_query))
        .order_by('-rank')[:100]
    )
    
    # 2. Vector Search (Semantic Match)
    vector_results = (
        KnowledgeBaseNode.objects
        .annotate(distance=L2Distance('embedding_vector', query_vector))
        .order_by('distance')[:100]
    )

    # 3. Reciprocal Rank Fusion (RRF)
    rrf_scores = {}
    
    # Calculate RRF for FTS
    for rank, node in enumerate(fts_results):
        rrf_scores[node.id] = {
            'node': node,
            'score': 1.0 / (rrf_k + rank + 1)
        }
        
    # Calculate RRF for Vector Search
    for rank, node in enumerate(vector_results):
        if node.id in rrf_scores:
            rrf_scores[node.id]['score'] += 1.0 / (rrf_k + rank + 1)
        else:
            rrf_scores[node.id] = {
                'node': node,
                'score': 1.0 / (rrf_k + rank + 1)
            }

    # Sort by combined RRF score
    sorted_results = sorted(rrf_scores.values(), key=lambda x: x['score'], reverse=True)
    
    return [item['node'] for item in sorted_results[:limit]]
