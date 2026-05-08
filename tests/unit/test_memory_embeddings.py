import math
from unittest.mock import patch

import pytest

from aio_framework import (
    MemoryConfig,
    PseudoEmbeddingEngine,
    RealEmbeddingEngine,
    EmbeddingEngineFactory,
    SENTENCE_TRANSFORMERS_AVAILABLE,
)


class TestPseudoEmbeddingEngine:
    def test_pseudo_embedding_determinism(self):
        engine = PseudoEmbeddingEngine()
        v1 = engine.embed("same text")
        v2 = engine.embed("same text")
        assert v1 == v2

    def test_pseudo_embedding_normalization(self):
        engine = PseudoEmbeddingEngine()
        vec = engine.embed("test text")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_pseudo_embedding_dimensions(self):
        engine = PseudoEmbeddingEngine()
        vec = engine.embed("dimension check")
        assert len(vec) == PseudoEmbeddingEngine.DIMENSION


class TestRealEmbeddingEngine:
    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_real_embedding_dimensions(self):
        engine = RealEmbeddingEngine("all-MiniLM-L6-v2")
        vec = engine.embed("hello world")
        assert len(vec) == engine.dimension
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6


class TestEmbeddingEngineFactory:
    def test_real_embedding_factory_when_disabled(self):
        cfg = MemoryConfig(use_real_embeddings=False)
        engine = EmbeddingEngineFactory.create(cfg)
        assert isinstance(engine, PseudoEmbeddingEngine)

    def test_real_embedding_factory_when_enabled_but_unavailable(self, caplog):
        cfg = MemoryConfig(use_real_embeddings=True)
        with patch("aio.memory.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", False):
            with caplog.at_level("WARNING", logger="aio.memory.embeddings"):
                engine = EmbeddingEngineFactory.create(cfg)
        assert isinstance(engine, PseudoEmbeddingEngine)
        assert "not installed" in caplog.text.lower() or "falling back" in caplog.text.lower()

    def test_real_embedding_factory_when_enabled_and_available(self):
        cfg = MemoryConfig(use_real_embeddings=True, embedding_model_name="all-MiniLM-L6-v2")
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            pytest.skip("sentence-transformers not installed")
        engine = EmbeddingEngineFactory.create(cfg)
        assert isinstance(engine, RealEmbeddingEngine)

    def test_real_embedding_factory_load_failure_fallback(self, caplog):
        cfg = MemoryConfig(use_real_embeddings=True, embedding_model_name="bad-model")
        with patch("aio.memory.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True):
            with patch(
                "aio.memory.embeddings.RealEmbeddingEngine.__init__",
                side_effect=RuntimeError("load failed"),
            ):
                with caplog.at_level("WARNING", logger="aio.memory.embeddings"):
                    engine = EmbeddingEngineFactory.create(cfg)
        assert isinstance(engine, PseudoEmbeddingEngine)
        assert "load failed" in caplog.text or "falling back" in caplog.text.lower()
