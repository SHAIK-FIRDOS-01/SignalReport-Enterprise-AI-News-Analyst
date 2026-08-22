import logging
import math
from typing import List, Optional
import numpy as np

logger = logging.getLogger("ai_engine.vector_service")

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VECTOR_DIMENSION = 384


class VectorEmbeddingService:
    """
    Zero-RAM, lightweight ONNX Vector Embedding Pipeline using FastEmbed and BAAI/bge-small-en-v1.5.
    Generates deterministic 384-dimensional dense vectors with L2 normalization.
    """

    _model_instance = None

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.model_name = model_name
        self._ensure_model_loaded()

    @classmethod
    def _ensure_model_loaded(cls):
        if cls._model_instance is None:
            try:
                from fastembed import TextEmbedding
                logger.info(f"Loading FastEmbed ONNX runtime with model '{DEFAULT_EMBEDDING_MODEL}'...")
                cls._model_instance = TextEmbedding(model_name=DEFAULT_EMBEDDING_MODEL)
            except Exception as e:
                logger.warning(f"Failed to load FastEmbed runtime ({e}). Activating deterministic fallback.")
                cls._model_instance = "fallback"

    def _normalize(self, vec: List[float]) -> List[float]:
        """Normalize vector to unit L2 norm."""
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            vec[0] = 1.0
            return vec
        return [round(x / norm, 6) for x in vec]

    def _fallback_vector(self, text: str) -> List[float]:
        """Deterministic cosine-friendly pseudo-embedding fallback for unit test isolation."""
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Seed 384 dimensions deterministically
        raw = []
        for i in range(VECTOR_DIMENSION):
            byte_val = h[i % len(h)]
            raw.append((byte_val / 255.0) - 0.5)
        return self._normalize(raw)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate 384-dimension dense L2-normalized embedding vector for text.
        """
        if not text or not text.strip():
            # Return normalized unit vector
            vec = [0.0] * VECTOR_DIMENSION
            vec[0] = 1.0
            return vec

        if self._model_instance and self._model_instance != "fallback":
            try:
                embeddings_gen = self._model_instance.embed([text])
                raw_vec = next(iter(embeddings_gen))
                vec_list = [float(x) for x in raw_vec]
                return self._normalize(vec_list)
            except Exception as e:
                logger.warning(f"FastEmbed inference error: {e}. Using deterministic fallback.")

        return self._fallback_vector(text)

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of strings.
        """
        if not texts:
            return []

        if self._model_instance and self._model_instance != "fallback":
            try:
                embeddings_gen = self._model_instance.embed(texts)
                return [self._normalize([float(x) for x in raw]) for raw in embeddings_gen]
            except Exception as e:
                logger.warning(f"FastEmbed batch error: {e}")

        return [self.generate_embedding(t) for t in texts]
