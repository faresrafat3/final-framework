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

    def test_real_embedding_when_enabled_and_available(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(
            dot=lambda *args: 1.0,
            __iter__=lambda self: iter([1.0, 0.0, 0.0, 0.0]),
        )
        with patch.dict("aio_framework.__dict__", {"SentenceTransformer": lambda name: mock_model, "SENTENCE_TRANSFORMERS_AVAILABLE": True}):
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
            mock_model.encode.assert_called_once()
            assert abs(sum(x * x for x in vec) - 1.0) < 1e-6

    def test_fallback_to_pseudo_when_disabled(self, mem):
        v1 = mem._embed("fallback")
        v2 = mem._embed("fallback")
        assert v1 == v2
        assert abs(sum(x * x for x in v1) - 1.0) < 1e-6

    def test_fallback_when_real_enabled_but_import_missing(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        with patch("aio_framework.SENTENCE_TRANSFORMERS_AVAILABLE", False):
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
            assert mem._embedding_model is None
            assert abs(sum(x * x for x in vec) - 1.0) < 1e-6

    def test_fallback_when_model_load_fails(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        def _raise(*args, **kwargs):
            raise RuntimeError("load failed")
        with patch.dict("aio_framework.__dict__", {"SentenceTransformer": _raise, "SENTENCE_TRANSFORMERS_AVAILABLE": True}):
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
            assert mem._embedding_model is None
            assert abs(sum(x * x for x in vec) - 1.0) < 1e-6


class TestRedisMemory:
    def test_redis_persistence_on_encode(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.ping.return_value = True
        with patch.dict("aio_framework.__dict__", {"redis_module": MagicMock(Redis=lambda **kwargs: mock_redis), "REDIS_AVAILABLE": True}):
            cfg = MemoryConfig(
                epiphany_ttl_seconds=1,
                consolidation_batch_size=2,
                retrieval_top_k=3,
                importance_threshold=0.3,
                forget_ttl_seconds=2,
                enable_redis=True,
            )
            mem = MemoryBridge(cfg, obs)
            state = make_initial_state("hello world")
            state["context_window"] = [{"role": "user", "content": "hello world", "turn": 1}]
            mem.encode(state)
            assert mock_redis.set.call_count >= 3
            args_list = [call.args for call in mock_redis.set.call_args_list]
            keys = {a[0] for a in args_list}
            assert "aio:memory:episodic" in keys
            assert "aio:memory:long_term" in keys
            assert "aio:memory:keyword_index" in keys

    def test_redis_load_on_init(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.side_effect = lambda key: {
            "aio:memory:episodic": '{"e1": {"id": "e1", "content": "loaded"}}',
            "aio:memory:long_term": '{"l1": {"id": "l1", "content": "lt"}}',
            "aio:memory:keyword_index": '{"loaded": ["e1"]}',
        }.get(key)
        with patch.dict("aio_framework.__dict__", {"redis_module": MagicMock(Redis=lambda **kwargs: mock_redis), "REDIS_AVAILABLE": True}):
            cfg = MemoryConfig(
                epiphany_ttl_seconds=1,
                consolidation_batch_size=2,
                retrieval_top_k=3,
                importance_threshold=0.3,
                forget_ttl_seconds=2,
                enable_redis=True,
            )
            mem = MemoryBridge(cfg, obs)
            assert mem._episodic.get("e1", {}).get("content") == "loaded"
            assert mem._long_term.get("l1", {}).get("content") == "lt"
            assert mem._keyword_index.get("loaded") == ["e1"]

    def test_redis_init_failure_fallback(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        def _raise(*args, **kwargs):
            raise ConnectionError("redis down")
        with patch.dict("aio_framework.__dict__", {"redis_module": MagicMock(Redis=_raise), "REDIS_AVAILABLE": True}):
            cfg = MemoryConfig(
                epiphany_ttl_seconds=1,
                consolidation_batch_size=2,
                retrieval_top_k=3,
                importance_threshold=0.3,
                forget_ttl_seconds=2,
                enable_redis=True,
            )
            mem = MemoryBridge(cfg, obs)
            assert mem._episodic == {}
            assert mem._long_term == {}
            assert mem._keyword_index == {}
            assert mem._redis._client is None

    def test_redis_runtime_failure_graceful(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        call_count = 0
        def _set(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 2:
                raise ConnectionError("redis write failed")
        mock_redis.set.side_effect = _set
        with patch.dict("aio_framework.__dict__", {"redis_module": MagicMock(Redis=lambda **kwargs: mock_redis), "REDIS_AVAILABLE": True}):
            cfg = MemoryConfig(
                epiphany_ttl_seconds=1,
                consolidation_batch_size=2,
                retrieval_top_k=3,
                importance_threshold=0.3,
                forget_ttl_seconds=2,
                enable_redis=True,
            )
            mem = MemoryBridge(cfg, obs)
            # First encode should succeed and persist
            state = make_initial_state("first")
            state["context_window"] = [{"role": "user", "content": "first", "turn": 1}]
            mem.encode(state)
            assert len(mem._episodic) == 1
            # Second encode will trigger _persist again; after Redis write fails, client is nulled
            state2 = make_initial_state("second")
            state2["context_window"] = [{"role": "user", "content": "second", "turn": 2}]
            mem.encode(state2)
            assert len(mem._episodic) == 2
            assert mem._redis._client is None
