import pytest

from aio_framework import (
    ContextManager,
    ContextConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def ctx_mgr():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    return ContextManager(ContextConfig(max_tokens=100, budget_reserve=10), obs)


class TestContextManager:
    def test_approximate_token_count(self):
        assert ContextManager.approximate_token_count("") == 1
        assert ContextManager.approximate_token_count("a" * 40) == 10

    def test_ingest_classifies_action_intent(self, ctx_mgr):
        state = make_initial_state("run the deployment script")
        state = ctx_mgr.ingest(state)
        assert state["intent"] == "action"
        assert state["turn"] == 1
        assert state["attention_map"]["execute"] > 0.5

    def test_ingest_classifies_analysis_intent(self, ctx_mgr):
        state = make_initial_state("analyze the error log")
        state = ctx_mgr.ingest(state)
        assert state["intent"] == "analysis"
        assert state["attention_map"]["verify"] > 0.1

    def test_ingest_classifies_coding_intent(self, ctx_mgr):
        state = make_initial_state("write a python function")
        state = ctx_mgr.ingest(state)
        assert state["intent"] == "coding"

    def test_sculpt_trims_window(self, ctx_mgr):
        state = make_initial_state("")
        state["context_window"] = [
            {"role": "user", "content": "x" * 400}
            for _ in range(10)
        ]
        state = ctx_mgr.sculpt(state)
        total = sum(
            ContextManager.approximate_token_count(str(m.get("content", "")))
            for m in state["context_window"]
        )
        assert total <= ctx_mgr.config.max_tokens - ctx_mgr.config.budget_reserve
        assert len(state["working_memory"]) > 0

    def test_route_attention_defaults_to_memory(self, ctx_mgr):
        state = make_initial_state("hello")
        state["attention_map"] = {"memory": 0.9, "execute": 0.1}
        assert ctx_mgr.route_attention(state) == "memory"

    def test_route_attention_boosts_recover_when_degraded(self, ctx_mgr):
        state = make_initial_state("hello")
        state["attention_map"] = {"memory": 0.4, "recover": 0.5}
        state["failure_state"] = "DEGRADED"
        target = ctx_mgr.route_attention(state)
        assert target == "recover"

    def test_find_prunable_index_prefers_non_system(self, ctx_mgr):
        window = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
        ]
        assert ctx_mgr._find_prunable_index(window) == 1

    def test_find_prunable_index_falls_back_to_zero(self, ctx_mgr):
        window = [{"role": "system", "content": "sys"}]
        assert ctx_mgr._find_prunable_index(window) == 0
