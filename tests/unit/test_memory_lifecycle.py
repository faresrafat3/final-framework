import math
import time
from unittest.mock import patch, MagicMock

import pytest

from aio_framework import (
    MemoryBridge,
    MemoryConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
    EbbinghausForgettingCurve,
    MemoryLifecycleEngine,
    LLMConsolidator,
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


class TestEbbinghausForgettingCurve:
    def test_retention_full_at_creation(self):
        config = MemoryConfig(forget_ttl_seconds=3600, importance_threshold=0.2, forgetting_curve_base=0.5)
        curve = EbbinghausForgettingCurve(config)
        entry = {"timestamp": time.time(), "importance": 0.5, "access_count": 1}
        assert curve.retention(entry) == pytest.approx(1.0, abs=1e-6)

    def test_retention_decays_over_time(self):
        config = MemoryConfig(forget_ttl_seconds=3600, importance_threshold=0.2, forgetting_curve_base=0.5)
        curve = EbbinghausForgettingCurve(config)
        now = time.time()
        entry = {"timestamp": now - 7200, "importance": 0.5, "access_count": 1}
        r = curve.retention(entry, now)
        assert 0.0 < r < 1.0

    def test_high_importance_retains_longer(self):
        config = MemoryConfig(forget_ttl_seconds=3600, importance_threshold=0.2, forgetting_curve_base=0.5)
        curve = EbbinghausForgettingCurve(config)
        now = time.time()
        low_imp = {"timestamp": now - 7200, "importance": 0.1, "access_count": 1}
        high_imp = {"timestamp": now - 7200, "importance": 0.9, "access_count": 1}
        assert curve.retention(high_imp, now) > curve.retention(low_imp, now)

    def test_frequent_access_retains_longer(self):
        config = MemoryConfig(forget_ttl_seconds=3600, importance_threshold=0.2, forgetting_curve_base=0.5)
        curve = EbbinghausForgettingCurve(config)
        now = time.time()
        rarely = {"timestamp": now - 7200, "importance": 0.5, "access_count": 1}
        often = {"timestamp": now - 7200, "importance": 0.5, "access_count": 100}
        assert curve.retention(often, now) > curve.retention(rarely, now)

    def test_should_forget_below_threshold(self):
        config = MemoryConfig(forget_ttl_seconds=1, importance_threshold=0.5, forgetting_curve_base=0.5)
        curve = EbbinghausForgettingCurve(config)
        now = time.time()
        entry = {"timestamp": now - 10, "importance": 0.1, "access_count": 1}
        assert curve.should_forget(entry, now) is True

    def test_should_not_forget_when_young(self):
        config = MemoryConfig(forget_ttl_seconds=3600, importance_threshold=0.2, forgetting_curve_base=0.5)
        curve = EbbinghausForgettingCurve(config)
        now = time.time()
        entry = {"timestamp": now - 0.9, "importance": 0.1, "access_count": 1}
        assert curve.should_forget(entry, now) is False

    def test_should_not_forget_important(self):
        config = MemoryConfig(forget_ttl_seconds=1, importance_threshold=0.5, forgetting_curve_base=0.5)
        curve = EbbinghausForgettingCurve(config)
        now = time.time()
        entry = {"timestamp": now - 2, "importance": 0.9, "access_count": 1}
        assert curve.should_forget(entry, now) is False


class TestLLMConsolidator:
    def test_consolidate_disabled_returns_none(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        config = MemoryConfig(enable_llm_consolidation=False)
        consolidator = LLMConsolidator(config, obs)
        entries = [{"id": "e1", "content": "hello", "role": "user", "importance": 0.5}]
        assert consolidator.consolidate(entries) is None

    def test_consolidate_empty_returns_none(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        config = MemoryConfig(enable_llm_consolidation=True)
        consolidator = LLMConsolidator(config, obs)
        assert consolidator.consolidate([]) is None

    def test_heuristic_consolidate_joins_snippets(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        config = MemoryConfig(consolidation_batch_size=2)
        consolidator = LLMConsolidator(config, obs)
        entries = [
            {"id": "e1", "content": "first snippet", "role": "user", "importance": 0.8},
            {"id": "e2", "content": "second snippet", "role": "assistant", "importance": 0.3},
        ]
        result = consolidator.heuristic_consolidate(entries)
        assert "first snippet" in result
        assert "second snippet" in result
        assert " | " in result

    def test_heuristic_consolidate_empty(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        config = MemoryConfig()
        consolidator = LLMConsolidator(config, obs)
        assert consolidator.heuristic_consolidate([]) == ""

    def test_llm_call_unavailable_returns_none(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        config = MemoryConfig(enable_llm_consolidation=True)
        consolidator = LLMConsolidator(config, obs)
        with patch("aio.memory.lifecycle.LANGCHAIN_CHAT_AVAILABLE", False):
            result = consolidator.consolidate([{"id": "e1", "content": "test", "role": "user"}])
        assert result is None


class TestMemoryLifecycleEngine:
    def test_run_consolidation_with_empty_batch(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        config = MemoryConfig(consolidation_batch_size=2)
        engine = MemoryLifecycleEngine(config, obs)
        result = engine.run_consolidation([], embed_fn=lambda x: [0.1] * 64, hash_fn=lambda x: "abc")
        assert result == []

    def test_run_consolidation_produces_entry(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        config = MemoryConfig(consolidation_batch_size=2)
        engine = MemoryLifecycleEngine(config, obs)
        entries = [
            {"id": "e1", "content": "hello world", "role": "user", "importance": 0.6},
        ]
        result = engine.run_consolidation(
            entries,
            embed_fn=lambda x: [0.1] * 64,
            hash_fn=lambda x: "abc123",
        )
        assert len(result) == 1
        assert result[0]["id"] == "abc123"
        assert result[0]["llm_consolidated"] is False
        assert result[0]["source_entry_ids"] == ["e1"]
        assert result[0]["access_count"] == 1

    def test_run_forget_returns_ids_to_purge(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        config = MemoryConfig(forget_ttl_seconds=1, importance_threshold=0.5, forgetting_curve_base=0.5)
        engine = MemoryLifecycleEngine(config, obs)
        now = time.time()
        store = {
            "old_low": {"timestamp": now - 10, "importance": 0.1, "access_count": 1},
            "old_high": {"timestamp": now - 10, "importance": 0.9, "access_count": 1},
            "young": {"timestamp": now - 0.5, "importance": 0.1, "access_count": 1},
        }
        purge_ids = engine.run_forget(store, now)
        assert "old_low" in purge_ids
        assert "old_high" not in purge_ids
        assert "young" not in purge_ids


class TestMemoryBridgeLifecycleIntegration:
    def test_consolidate_creates_lt_entry(self, mem):
        old = time.time() - 10
        mem._episodic["old1"] = {"id": "old1", "content": "a", "timestamp": old, "verification_passed": True}
        mem._episodic["old2"] = {"id": "old2", "content": "b", "timestamp": old, "verification_passed": True}
        state = make_initial_state("")
        state = mem.consolidate(state)
        assert len(mem._long_term) == 1
        lt_entry = list(mem._long_term.values())[0]
        assert "source_entry_ids" in lt_entry
        assert set(lt_entry["source_entry_ids"]) == {"old1", "old2"}
        assert "old1" not in mem._episodic
        assert "old2" not in mem._episodic

    def test_forget_uses_adaptive_curve(self, mem):
        now = time.time()
        mem._episodic["f1"] = {"id": "f1", "content": "temp", "timestamp": now - 10, "importance": 0.1, "access_count": 1}
        mem._episodic["f2"] = {"id": "f2", "content": "keep", "timestamp": now - 10, "importance": 0.9, "access_count": 1}
        state = make_initial_state("")
        state = mem.forget(state)
        assert "f1" not in mem._episodic
        assert "f2" in mem._episodic

    def test_retrieve_bumps_access_count(self, mem):
        mem._episodic["r1"] = {
            "id": "r1", "content": "python asyncio patterns",
            "timestamp": time.time(), "embedding": mem._embed("python asyncio patterns"),
            "importance": 0.8, "verification_passed": True,
        }
        mem._index_keywords("r1", "python asyncio patterns")
        state = make_initial_state("python asyncio")
        assert mem._episodic["r1"].get("access_count", 0) == 0
        state = mem.retrieve(state)
        assert mem._episodic["r1"]["access_count"] == 1
        state = mem.retrieve(state)
        assert mem._episodic["r1"]["access_count"] == 2

    def test_retrieve_bumps_access_count_long_term(self, mem):
        mem._long_term["lt1"] = {
            "id": "lt1", "content": "machine learning basics",
            "timestamp": time.time(), "embedding": mem._embed("machine learning basics"),
            "importance": 0.7, "verification_passed": True,
        }
        mem._index_keywords("lt1", "machine learning basics")
        state = make_initial_state("machine learning")
        assert mem._long_term["lt1"].get("access_count", 0) == 0
        state = mem.retrieve(state)
        assert mem._long_term["lt1"]["access_count"] == 1
