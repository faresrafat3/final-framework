"""Memory Bridge embedding subsystem.

Provides pluggable embedding engines for the dual-memory bridge.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Optional, Sequence

from ..config.deps import (
    SENTENCE_TRANSFORMERS_AVAILABLE,
    SentenceTransformer,
)
from ..config.models import MemoryConfig

logger = logging.getLogger(__name__)


class BaseEmbeddingEngine(ABC):
    """Abstract base for embedding engines."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding vector dimensionality."""
        ...

    @property
    @abstractmethod
    def is_real(self) -> bool:
        """Return *True* when backed by a real model, else *False*."""
        ...

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Return a normalized embedding vector for *text*."""
        ...

    def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        """Return normalized embedding vectors for *texts*."""
        return [self.embed(text) for text in texts]


def _normalize_vector(vector: Sequence[float]) -> List[float]:
    values = [float(v) for v in vector]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def _deterministic_unit_vector(text: str, dimension: int) -> List[float]:
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
    rng = random.Random(seed)
    values = [rng.uniform(-1.0, 1.0) for _ in range(dimension)]
    return _normalize_vector(values)


class RealEmbeddingEngine(BaseEmbeddingEngine):
    """Embedding engine backed by ``sentence-transformers`` with lazy loading.

    Real model loading is deferred until the first embed call via
    :meth:`_ensure_loaded`. If real embeddings are disabled or unavailable,
    the engine transparently falls back to deterministic pseudo-embeddings.
    """

    DEFAULT_DIMENSION = 384

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", enable_real: bool = True) -> None:
        self.model_name = model_name
        self.enable_real = enable_real
        self._dimension = self.DEFAULT_DIMENSION
        self._model: Optional[Any] = None
        self._load_attempted = False
        self._fallback_engine = PseudoEmbeddingEngine(dimension=self._dimension)

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def is_real(self) -> bool:
        return self._model is not None

    def _ensure_loaded(self) -> None:
        if self._model is not None or self._load_attempted:
            return

        self._load_attempted = True

        if not self.enable_real:
            logger.warning("Real embeddings disabled; using deterministic pseudo-embeddings.")
            return

        if not SENTENCE_TRANSFORMERS_AVAILABLE or SentenceTransformer is None:
            logger.warning(
                "Real embeddings requested but sentence-transformers is not installed. "
                "Falling back to pseudo-embeddings."
            )
            return

        try:
            self._model = SentenceTransformer(self.model_name)
            if hasattr(self._model, "get_sentence_embedding_dimension"):
                model_dim = self._model.get_sentence_embedding_dimension()
                if isinstance(model_dim, int) and model_dim > 0:
                    self._dimension = model_dim
                    self._fallback_engine = PseudoEmbeddingEngine(dimension=self._dimension)
        except Exception as exc:  # pragma: no cover
            self._model = None
            logger.warning(
                "Failed to load embedding model '%s': %s. Falling back to pseudo-embeddings.",
                self.model_name,
                exc,
            )

    def _embed_real(self, text: str) -> List[float]:
        assert self._model is not None
        encoded = self._model.encode(text, convert_to_numpy=True)
        vector = _normalize_vector(encoded)
        if len(vector) != self._dimension:
            self._dimension = len(vector)
            self._fallback_engine = PseudoEmbeddingEngine(dimension=self._dimension)
        return vector

    def embed(self, text: str) -> List[float]:
        self._ensure_loaded()
        if self._model is not None:
            return self._embed_real(text)
        return self._fallback_engine.embed(text)

    def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        batch = list(texts)
        if not batch:
            return []

        self._ensure_loaded()
        if self._model is None:
            return self._fallback_engine.embed_batch(batch)

        encoded_batch = self._model.encode(batch, convert_to_numpy=True)
        vectors = [_normalize_vector(row) for row in encoded_batch]
        if vectors and len(vectors[0]) != self._dimension:
            self._dimension = len(vectors[0])
            self._fallback_engine = PseudoEmbeddingEngine(dimension=self._dimension)
        return vectors


class PseudoEmbeddingEngine(BaseEmbeddingEngine):
    """Deterministic hash-based fallback producing normalized vectors."""

    DIMENSION = 64

    def __init__(self, dimension: int = DIMENSION) -> None:
        self._dimension = int(dimension) if dimension > 0 else self.DIMENSION

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def is_real(self) -> bool:
        return False

    def embed(self, text: str) -> List[float]:
        return _deterministic_unit_vector(text, self._dimension)

    def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        return [self.embed(text) for text in texts]


class EmbeddingEngineFactory:
    """Factory that selects the appropriate engine based on config."""

    @staticmethod
    def create(config: MemoryConfig) -> BaseEmbeddingEngine:
        """Build the configured embedding engine with safe fallback behavior."""
        if config.use_real_embeddings and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                return RealEmbeddingEngine(
                    model_name=config.embedding_model_name,
                    enable_real=True,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "Failed to initialize real embedding engine '%s': %s. "
                    "Falling back to pseudo-embeddings.",
                    config.embedding_model_name,
                    exc,
                )
                return PseudoEmbeddingEngine(dimension=config.vector_dimension)

        if config.use_real_embeddings and not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning(
                "Real embeddings requested but sentence-transformers is not installed. "
                "Falling back to pseudo-embeddings."
            )

        return PseudoEmbeddingEngine(dimension=config.vector_dimension)
