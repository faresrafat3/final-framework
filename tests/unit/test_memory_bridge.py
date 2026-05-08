import time
from unittest.mock import patch, MagicMock

import pytest

from aio_framework import (
    MemoryBridge,
    MemoryConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
    SENTENCE_TRANSFORMERS_AVAILABLE,
    PseudoEmbeddingEngine,
    RealEmbeddingEngine,
)


@pytest.fixture
def mem():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    return MemoryBridge(MemoryConfig(
        epiphany_ttl_seconds=1,
        consolidation_batch_size=2,
        retrieval_top_k=3,
        importance_threshold=0.3,
        forget_ttl_seconds=2,
    ), obs)


class TestMemoryBridge:
    def test_hash_consistency(self, mem):
        h1 = mem._hash("hello")
        h2 = mem._hash("hello")
        assert h1 == h2
        assert len(h1) == 16

    def test_embed_deterministic(self, mem):
        v1 = mem._embed("test")
        v2 = mem._embed("test")
        assert v1 == v2
        assert abs(sum(x * x for x in v1) - 1.0) < 1e-6

    def test_cosine_similarity_identical(self, mem):
        v = [0.5, 0.5]
        assert mem._cosine_similarity(v, v) == pytest.approx(0.5, rel=1e-3)

    def test_mia_score_range(self, mem):
        entry = {"role": "user", "content": "error occurred", "timestamp": time.time()}
        score = mem._mia_score(entry)
        assert 0.0 <= score <= 1.0

    def test_encode_populates_episodic(self, mem):
        state = make_initial_state("hello world")
        state["context_window"] = [{"role": "user", "content": "hello world", "turn": 1}]
        state = mem.encode(state)
        assert len(mem._episodic) == 1

    def test_verify_deduplicates(self, mem):
        mem._episodic["a"] = {"content": "dup", "timestamp": time.time()}
        mem._episodic["b"] = {"content": "dup", "timestamp": time.time()}
        state = make_initial_state("")
        state = mem.verify(state)
        contents = [e["content"] for e in mem._episodic.values()]
        assert contents.count("dup") == 1

    def test_verify_marks_long_content_failed(self, mem):
        mem._episodic["x"] = {"content": "x" * 10001, "timestamp": time.time()}
        state = make_initial_state("")
        state = mem.verify(state)
        assert mem._episodic["x"]["verification_passed"] is False

    def test_consolidate_moves_to_long_term(self, mem):
        old = time.time() - 10
        mem._episodic["old1"] = {"id": "old1", "content": "a", "timestamp": old, "verification_passed": True}
        mem._episodic["old2"] = {"id": "old2", "content": "b", "timestamp": old, "verification_passed": True}
        state = make_initial_state("")
        state = mem.consolidate(state)
        assert "old1" in mem._long_term or "old2" in mem._long_term

    def test_retrieve_returns_results(self, mem):
        mem._episodic["r1"] = {
            "id": "r1", "content": "python asyncio patterns",
            "timestamp": time.time(), "embedding": mem._embed("python asyncio patterns"),
            "importance": 0.8, "verification_passed": True,
        }
        mem._index_keywords("r1", "python asyncio patterns")
        state = make_initial_state("python asyncio")
        state = mem.retrieve(state)
        assert len(state["working_memory"]) > 0
        assert state["memory_confidence"] > 0.0

    def test_forget_prunes_low_importance(self, mem):
        mem._episodic["f1"] = {
            "id": "f1", "content": "temp",
            "timestamp": time.time() - 10, "importance": 0.1,
        }
        state = make_initial_state("")
        state = mem.forget(state)
        assert "f1" not in mem._episodic

    def test_retrieve_top_k_respected(self, mem):
        for i in range(10):
            content = f"memory item {i}"
            eid = mem._hash(content)
            mem._episodic[eid] = {
                "id": eid, "content": content,
                "timestamp": time.time(), "embedding": mem._embed(content),
                "importance": 0.5, "verification_passed": True,
            }
            mem._index_keywords(eid, content)
        state = make_initial_state("memory item")
        state = mem.retrieve(state)
        assert len(state["working_memory"]) <= mem.config.retrieval_top_k

    def test_memory_bridge_uses_embedding_engine(self, mem):
        assert hasattr(mem, "_embedding_engine")
        engine = mem._embedding_engine
        v1 = engine.embed("delegation test")
        v2 = mem._embed("delegation test")
        assert v1 == v2

    def test_real_embedding_when_enabled_and_available(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        mock_engine = MagicMock()
        mock_engine.embed.return_value = [1.0, 0.0, 0.0, 0.0]
        with patch("aio.memory.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True):
            with patch("aio.memory.embeddings.RealEmbeddingEngine", return_value=mock_engine):
                cfg = MemoryConfig(
                    epiphany_ttl_seconds=1,
                    consolidation_batch_size=2,
                    retrieval_top_k=3,
                    importance_threshold=0.3,
                    forget_ttl_seconds=2,
                    use_real_embeddings=True,
                )
                mem = MemoryBridge(cfg, obs)
                vec = mem._embed("hello")
                mock_engine.embed.assert_called_once_with("hello")
                assert vec == [1.0, 0.0, 0.0, 0.0]

    def test_fallback_to_pseudo_when_disabled(self, mem):
        v1 = mem._embed("fallback")
        v2 = mem._embed("fallback")
        assert v1 == v2
        assert abs(sum(x * x for x in v1) - 1.0) < 1e-6

    def test_fallback_when_real_enabled_but_import_missing(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        with patch("aio.memory.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", False):
            cfg = MemoryConfig(
                epiphany_ttl_seconds=1,
                consolidation_batch_size=2,
                retrieval_top_k=3,
                importance_threshold=0.3,
                forget_ttl_seconds=2,
                use_real_embeddings=True,
            )
            mem = MemoryBridge(cfg, obs)
            vec = mem._embed("hello")
            assert isinstance(mem._embedding_engine, PseudoEmbeddingEngine)
            assert abs(sum(x * x for x in vec) - 1.0) < 1e-6

    def test_fallback_when_model_load_fails(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        with patch("aio.memory.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True):
            with patch(
                "aio.memory.embeddings.RealEmbeddingEngine.__init__",
                side_effect=RuntimeError("load failed"),
            ):
                cfg = MemoryConfig(
                    epiphany_ttl_seconds=1,
                    consolidation_batch_size=2,
                    retrieval_top_k=3,
                    importance_threshold=0.3,
                    forget_ttl_seconds=2,
                    use_real_embeddings=True,
                )
                mem = MemoryBridge(cfg, obs)
                vec = mem._embed("hello")
                assert isinstance(mem._embedding_engine, PseudoEmbeddingEngine)
                assert abs(sum(x * x for x in vec) - 1.0) < 1e-6
