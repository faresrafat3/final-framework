import pytest

from aio_framework import (
    MultiAgentCoordinator,
    MultiAgentConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def ma_layer():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = MultiAgentConfig(enable=True)
    return MultiAgentCoordinator(cfg, obs)


class TestMultiAgentCoordinator:
    def test_decompose_for_coding(self, ma_layer):
        state = make_initial_state("write a function")
        state["intent"] = "coding"
        state = ma_layer.decompose(state)
        plan = state["coordination_plan"]
        assert plan["intent"] == "coding"
        agents = [s["agent"] for s in plan["subtasks"]]
        assert "planner" in agents
        assert "coder" in agents
        assert "safety_officer" in agents

    def test_decompose_for_analysis(self, ma_layer):
        state = make_initial_state("analyze data")
        state["intent"] = "analysis"
        state = ma_layer.decompose(state)
        plan = state["coordination_plan"]
        agents = [s["agent"] for s in plan["subtasks"]]
        assert "analyst" in agents

    def test_decompose_for_general(self, ma_layer):
        state = make_initial_state("hello")
        state["intent"] = "general"
        state = ma_layer.decompose(state)
        plan = state["coordination_plan"]
        assert len(plan["subtasks"]) <= 2

    def test_dispatch_generates_outputs(self, ma_layer):
        state = make_initial_state("test")
        state["coordination_plan"] = {
            "subtasks": [
                {"id": "st-1", "agent": "planner", "description": "Plan"},
                {"id": "st-2", "agent": "coder", "description": "Code"},
            ]
        }
        state = ma_layer.dispatch(state)
        outputs = state["agent_outputs"]
        assert "st-1" in outputs
        assert "st-2" in outputs
        assert outputs["st-1"]["confidence"] > 0.0

    def test_aggregate_computes_consensus(self, ma_layer):
        state = make_initial_state("test")
        state["agent_outputs"] = {
            "st-1": {"confidence": 0.9},
            "st-2": {"confidence": 0.9},
        }
        state = ma_layer.aggregate(state)
        assert state["consensus_score"] > 0.8

    def test_aggregate_low_variance(self, ma_layer):
        state = make_initial_state("test")
        state["agent_outputs"] = {
            "st-1": {"confidence": 0.9},
            "st-2": {"confidence": 0.3},
        }
        state = ma_layer.aggregate(state)
        assert state["consensus_score"] < 0.7

    def test_synthesize_unifies_plan(self, ma_layer):
        state = make_initial_state("test")
        state["agent_outputs"] = {
            "st-1": {"result": "part A"},
            "st-2": {"result": "part B"},
        }
        state = ma_layer.synthesize(state)
        assert "part A" in state["plan"]
        assert "part B" in state["plan"]

    def test_default_registry(self, ma_layer):
        assert set(ma_layer._registry.keys()) == {"coder", "analyst", "planner", "safety_officer"}
