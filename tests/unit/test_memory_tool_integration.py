from unittest.mock import patch

from aio_framework import (
    MemoryBridge,
    MemoryConfig,
    ObservabilityConfig,
    ObservabilityLayer,
    ToolGate,
    ToolGateConfig,
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
        forget_ttl_seconds=10,
    )
    return MemoryBridge(cfg, obs)


def test_memory_tools_registered_when_enabled_with_memory_bridge():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    mem = _make_memory_bridge()
    tg = ToolGate(ToolGateConfig(enable_memory_tools=True), obs, memory_bridge=mem)

    assert "store_memory" in tg._registry
    assert "recall_memory" in tg._registry


def test_memory_tools_not_registered_when_disabled():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    mem = _make_memory_bridge()
    tg = ToolGate(ToolGateConfig(enable_memory_tools=False), obs, memory_bridge=mem)

    assert "store_memory" not in tg._registry
    assert "recall_memory" not in tg._registry


def test_store_memory_tool_persists_to_long_term_memory():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    mem = _make_memory_bridge()
    tg = ToolGate(ToolGateConfig(enable_memory_tools=True), obs, memory_bridge=mem)

    state = make_initial_state("")
    state["plan"] = "remember this architecture decision"
    with patch.object(tg, "route", return_value="store_memory"):
        state = tg.execute(state)

    assert state["execution_result"]["success"] is True
    assert len(mem._long_term) == 1


def test_recall_memory_tool_returns_entries():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    mem = _make_memory_bridge()
    mem.store_long_term("postgres migration completed", role="system", importance=0.9)

    tg = ToolGate(ToolGateConfig(enable_memory_tools=True), obs, memory_bridge=mem)
    state = make_initial_state("")
    state["plan"] = "recall_memory postgres top_k=1"

    with patch.object(tg, "route", return_value="recall_memory"):
        state = tg.execute(state)

    assert state["execution_result"]["success"] is True
    assert "entries" in state["execution_result"]["stdout"]
