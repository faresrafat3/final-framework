import time
from unittest.mock import MagicMock

from aio_framework import (
    MemoryBridge,
    MemoryConfig,
    ObservabilityConfig,
    ObservabilityLayer,
    make_initial_state,
)


def _make_memory_bridge() -> MemoryBridge:
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = MemoryConfig(
        backend_type="memory",
        epiphany_ttl_seconds=1,
        consolidation_batch_size=2,
        retrieval_top_k=3,
        importance_threshold=0.2,
        forget_ttl_seconds=2,
    )
    return MemoryBridge(cfg, obs)


def test_verify_removes_duplicate_entries_from_keyword_index():
    mem = _make_memory_bridge()
    now = time.time()
    mem._episodic["a"] = {"id": "a", "content": "duplicate content", "timestamp": now}
    mem._episodic["b"] = {"id": "b", "content": "duplicate    content", "timestamp": now}
    mem._index_keywords("a", "duplicate content")
    mem._index_keywords("b", "duplicate content")

    state = make_initial_state("")
    mem.verify(state)

    assert len(mem._episodic) == 1
    ids = {eid for bucket in mem._keyword_index.values() for eid in bucket}
    assert ids == set(mem._episodic.keys())


def test_store_long_term_and_recall_increment_access_count():
    mem = _make_memory_bridge()

    entry = mem.store_long_term("distributed systems note", role="system", importance=0.8)
    recalled = mem.recall("distributed systems", top_k=1)

    assert recalled
    assert recalled[0]["id"] == entry["id"]
    assert mem._long_term[entry["id"]]["access_count"] >= 1


def test_retrieve_persists_access_count_via_backend_sync():
    mem = _make_memory_bridge()
    mem._backend.sync = MagicMock()

    mem._episodic["r1"] = {
        "id": "r1",
        "content": "python asyncio retrieval",
        "timestamp": time.time(),
        "embedding": mem._embed("python asyncio retrieval"),
        "importance": 0.9,
        "verification_passed": True,
        "access_count": 0,
    }
    mem._index_keywords("r1", "python asyncio retrieval")

    state = make_initial_state("python asyncio")
    mem.retrieve(state)

    assert mem._episodic["r1"]["access_count"] >= 1
    assert mem._backend.sync.called
