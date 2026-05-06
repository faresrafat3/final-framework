import time
from unittest.mock import patch

import pytest

from aio_framework import (
    MemoryBridge,
    MemoryConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
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
