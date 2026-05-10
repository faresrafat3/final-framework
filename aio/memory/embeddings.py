"""Memory Bridge embedding subsystem.

Provides pluggable embedding engines for the dual-memory bridge.
"""

from __future__ import annotations

import hashlib
import logging
import random
from abc import ABC, abstractmethod
from typing import List

from ..config.deps import SENTENCE_TRANSFORMERS_AVAILABLE
from ..config.models import MemoryConfig

logger = logging.getLogger(__name__)


class BaseEmbeddingEngine(ABC):
    """Abstract base for embedding engines."""

    dimension: int = 0

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Return a normalized embedding vector for *text*."""
        ...


class RealEmbeddingEngine(BaseEmbeddingEngine):
    """Production embedding engine backed by ``sentence-transformers``.

    Attributes:
        model: The loaded ``SentenceTransformer`` instance.
        dimension: Expected vector dimensionality (default 384 for
            ``all-MiniLM-L6-v2``).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.dimension = 384

    def embed(self, text: str) -> List[float]:
        vec = self.model.encode(text, convert_to_numpy=True)
        norm = float(vec.dot(vec)) ** 0.5 or 1.0
        return [float(v) / norm for v in vec]


class PseudoEmbeddingEngine(BaseEmbeddingEngine):
    """Deterministic hash-based fallback producing 64-dim normalized vectors."""

    dimension: int = 64
    DIMENSION = 64

    def embed(self, text: str) -> List[float]:
        h = int(hashlib.sha256(text.encode()).hexdigest(), 16)
        random.seed(h)
        vec = [random.random() for _ in range(self.DIMENSION)]
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


class EmbeddingEngineFactory:
    """Factory that selects the appropriate engine based on config."""

    @staticmethod
    def create(config: MemoryConfig) -> BaseEmbeddingEngine:
        """Return a :class:`RealEmbeddingEngine` when
        ``config.use_real_embeddings`` is *True* and
        ``sentence-transformers`` is available; otherwise fall back to
        :class:`PseudoEmbeddingEngine` with a warning log.
        """
        if config.use_real_embeddings and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                return RealEmbeddingEngine(config.embedding_model_name)
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "Failed to load embedding model '%s': %s. "
                    "Falling back to pseudo-embeddings.",
                    config.embedding_model_name,
                    exc,
                )
                return PseudoEmbeddingEngine()

        if config.use_real_embeddings and not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning(
                "Real embeddings requested but sentence-transformers is not installed. "
                "Falling back to pseudo-embeddings."
            )

        return PseudoEmbeddingEngine()
