import logging
import math
from typing import Optional, List, Dict, Any
from django.db import connection
from django.db.models import Q
from apps.knowledge_base.models import KnowledgeBaseNode

logger = logging.getLogger(__name__)


def compute_rrf_score(
    fts_rank: Optional[int] = None,
    vec_rank: Optional[int] = None,
    k: int = 60
) -> float:
    """
    Compute Reciprocal Rank Fusion (RRF) score:
    RRF(d) = sum_{m in M} (1 / (k + r_m(d)))
    """
    score = 0.0
    if fts_rank is not None and fts_rank > 0:
        score += 1.0 / (k + fts_rank)
    if vec_rank is not None and vec_rank > 0:
        score += 1.0 / (k + vec_rank)
    return round(score, 8)


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class HybridSearchService:
    """
    Hybrid RAG Search Engine combining Sparse Full-Text Search (BM25/tsvector)
    and Dense Semantic Vector Search (pgvector 384D) via Reciprocal Rank Fusion (RRF).
    """

    def hybrid_search(
        self,
        query: str,
        query_vector: Optional[List[float]] = None,
        limit: int = 10,
        k: int = 60,
        signal_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute blended hybrid retrieval ranking candidate documents via RRF.
        """
        qs = KnowledgeBaseNode.objects.all()
        if signal_type:
            qs = qs.filter(signal_type=signal_type)

        nodes = list(qs)
        if not nodes:
            return []

        # 1. Sparse Retrieval (Full-Text Search / Lexical match)
        fts_ranked_ids: List[int] = []
        if query:
            query_terms = [t.lower() for t in query.split() if len(t) > 1]
            
            # Check if Postgres tsvector full text search is active
            if connection.vendor == 'postgresql':
                try:
                    from django.contrib.postgres.search import SearchQuery, SearchRank
                    search_query = SearchQuery(query)
                    fts_nodes = (
                        qs.filter(search_vector=search_query)
                        .annotate(rank=SearchRank('search_vector', search_query))
                        .order_by('-rank')[:limit * 3]
                    )
                    fts_ranked_ids = [n.id for n in fts_nodes]
                except Exception as e:
                    logger.debug(f"Postgres FTS fallback to lexical: {e}")

            if not fts_ranked_ids:
                # Portable lexical ranking for SQLite test isolation
                scored_nodes = []
                for n in nodes:
                    text_corpus = f"{n.title} {n.content_raw} {n.content_processed}".lower()
                    score = 0
                    for term in query_terms:
                        if term in n.title.lower():
                            score += 3  # Title match weighting
                        if term in text_corpus:
                            score += 1
                    if score > 0:
                        scored_nodes.append((score, n.id))
                scored_nodes.sort(key=lambda x: x[0], reverse=True)
                fts_ranked_ids = [node_id for _, node_id in scored_nodes[:limit * 3]]

        # 2. Dense Semantic Vector Retrieval
        vec_ranked_ids: List[int] = []
        if query_vector:
            if connection.vendor == 'postgresql':
                try:
                    from pgvector.django import CosineDistance
                    vec_nodes = qs.exclude(embedding_vector__isnull=True).order_by(
                        CosineDistance('embedding_vector', query_vector)
                    )[:limit * 3]
                    vec_ranked_ids = [n.id for n in vec_nodes]
                except Exception as e:
                    logger.debug(f"pgvector query fallback to python cosine: {e}")

            if not vec_ranked_ids:
                # Portable vector cosine ranking
                scored_vecs = []
                for n in nodes:
                    if n.embedding_vector:
                        sim = _cosine_similarity(query_vector, n.embedding_vector)
                        if sim > 0.05:
                            scored_vecs.append((sim, n.id))
                scored_vecs.sort(key=lambda x: x[0], reverse=True)
                vec_ranked_ids = [node_id for _, node_id in scored_vecs[:limit * 3]]

        # 3. Reciprocal Rank Fusion (RRF)
        candidate_ids = set(fts_ranked_ids) | set(vec_ranked_ids)
        if not candidate_ids:
            # Fallback to recent nodes if query returned empty
            candidate_ids = {n.id for n in nodes[:limit]}

        fts_rank_map = {node_id: idx + 1 for idx, node_id in enumerate(fts_ranked_ids)}
        vec_rank_map = {node_id: idx + 1 for idx, node_id in enumerate(vec_ranked_ids)}
        node_map = {n.id: n for n in nodes if n.id in candidate_ids}

        fused_results = []
        for node_id in candidate_ids:
            node = node_map.get(node_id)
            if not node:
                continue

            r_fts = fts_rank_map.get(node_id)
            r_vec = vec_rank_map.get(node_id)
            rrf_score = compute_rrf_score(fts_rank=r_fts, vec_rank=r_vec, k=k)

            fused_results.append({
                "id": node.id,
                "title": node.title,
                "source_url": node.source_url,
                "content_processed": node.content_processed,
                "signal_type": node.signal_type,
                "published_at": node.published_at.isoformat() if node.published_at else None,
                "rrf_score": rrf_score,
                "fts_rank": r_fts,
                "vec_rank": r_vec,
                "metadata_json": node.metadata_json,
            })

        # Sort descending by RRF score
        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused_results[:limit]
