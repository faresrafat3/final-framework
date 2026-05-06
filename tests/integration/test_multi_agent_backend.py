import pytest

from aio_framework import (
    MultiAgentConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
    SimulatedMultiAgentBackend,
    LangGraphMultiAgentBackend,
    MultiAgentCoordinator,
    build_aio_graph,
    AIOConfig,
)


@pytest.fixture
def obs():
    return ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))


@pytest.fixture
def registry():
    return {
        "coder": {"role": "Implementation", "strengths": ["code", "debug", "refactor"]},
        "analyst": {"role": "Analysis", "strengths": ["data", "patterns", "summary"]},
        "planner": {"role": "Strategy", "strengths": ["decompose", "dependencies", "schedule"]},
        "safety_officer": {"role": "Safety", "strengths": ["risk", "compliance", "boundaries"]},
    }


class TestSimulatedMultiAgentBackend:
    def test_dispatch_returns_outputs(self, obs, registry):
        cfg = MultiAgentConfig(enable=True)
        backend = SimulatedMultiAgentBackend(cfg, obs, registry)
        state = make_initial_state("test")
        state["coordination_plan"] = {
            "subtasks": [
                {"id": "st-1", "agent": "planner", "description": "Plan"},
                {"id": "st-2", "agent": "coder", "description": "Code"},
            ]
        }
        result = backend.dispatch(state)
        assert "st-1" in result["agent_outputs"]
        assert "st-2" in result["agent_outputs"]
        assert result["agent_outputs"]["st-1"]["confidence"] > 0.0


class TestLangGraphMultiAgentBackend:
    def test_dispatch_builds_subgraph_and_returns_outputs(self, obs, registry):
        cfg = MultiAgentConfig(enable=True)
        backend = LangGraphMultiAgentBackend(cfg, obs, registry)
        state = make_initial_state("test")
        state["coordination_plan"] = {
            "subtasks": [
                {"id": "st-1", "agent": "planner", "description": "Plan"},
                {"id": "st-2", "agent": "coder", "description": "Code"},
            ]
        }
        result = backend.dispatch(state)
        assert "st-1" in result["agent_outputs"]
        assert "st-2" in result["agent_outputs"]
        assert result["consensus_score"] is not None
        for entry in result["agent_outputs"].values():
            assert "LangGraph sub-agent output" in entry["result"]

    def test_dispatch_with_custom_callables(self, obs, registry):
        def custom_coder(state):
            state["agent_outputs"] = state.get("agent_outputs", {})
            state["agent_outputs"]["st-custom"] = {
                "agent": "coder",
                "confidence": 0.99,
                "result": "custom code result",
            }
            return state

        cfg = MultiAgentConfig(enable=True)
        backend = LangGraphMultiAgentBackend(
            cfg, obs, registry, agent_callables={"coder": custom_coder}
        )
        state = make_initial_state("test")
        state["coordination_plan"] = {
            "subtasks": [
                {"id": "st-1", "agent": "planner", "description": "Plan"},
                {"id": "st-2", "agent": "coder", "description": "Code"},
            ]
        }
        result = backend.dispatch(state)
        assert "st-custom" in result["agent_outputs"]
        assert result["agent_outputs"]["st-custom"]["result"] == "custom code result"

    def test_fallback_on_exception(self, obs, registry):
        class BrokenBackend(LangGraphMultiAgentBackend):
            def _run_subgraph(self, state):
                raise RuntimeError("boom")

        cfg = MultiAgentConfig(enable=True)
        backend = BrokenBackend(cfg, obs, registry)
        state = make_initial_state("test")
        state["coordination_plan"] = {
            "subtasks": [
                {"id": "st-1", "agent": "planner", "description": "Plan"},
            ]
        }
        result = backend.dispatch(state)
        assert "st-1" in result["agent_outputs"]
        assert result["metrics"].get("multi_agent_fallback_reason") == "boom"


class TestMultiAgentCoordinatorBackendSwitch:
    def test_uses_simulated_backend_by_default(self, obs):
        cfg = MultiAgentConfig(enable=True)
        coord = MultiAgentCoordinator(cfg, obs)
        assert coord._langgraph_backend is None
        state = make_initial_state("test")
        state["coordination_plan"] = {
            "subtasks": [
                {"id": "st-1", "agent": "planner", "description": "Plan"},
            ]
        }
        result = coord.dispatch(state)
        assert "Simulated output" in result["agent_outputs"]["st-1"]["result"]

    def test_uses_langgraph_backend_when_enabled(self, obs):
        cfg = MultiAgentConfig(enable=True, use_langgraph_backend=True)
        coord = MultiAgentCoordinator(cfg, obs)
        assert coord._langgraph_backend is not None
        state = make_initial_state("test")
        state["coordination_plan"] = {
            "subtasks": [
                {"id": "st-1", "agent": "planner", "description": "Plan"},
            ]
        }
        result = coord.dispatch(state)
        assert "LangGraph sub-agent output" in result["agent_outputs"]["st-1"]["result"]

    def test_aggregate_and_synthesize_with_langgraph_backend(self, obs):
        cfg = MultiAgentConfig(enable=True, use_langgraph_backend=True)
        coord = MultiAgentCoordinator(cfg, obs)
        state = make_initial_state("test")
        state["coordination_plan"] = {
            "subtasks": [
                {"id": "st-1", "agent": "planner", "description": "Plan"},
                {"id": "st-2", "agent": "coder", "description": "Code"},
            ]
        }
        state = coord.dispatch(state)
        state = coord.aggregate(state)
        assert state["consensus_score"] is not None
        state = coord.synthesize(state)
        assert "LangGraph sub-agent output" in state["plan"]


class TestGraphIntegrationWithLangGraphBackend:
    def test_graph_runs_with_langgraph_multi_agent_enabled(self):
        cfg = AIOConfig(enable_priority_3=True)
        cfg.multi_agent.use_langgraph_backend = True
        app = build_aio_graph(cfg)
        state = make_initial_state("write a python function")
        state["intent"] = "coding"
        result = app.invoke(state)
        assert result["output"] is not None
        assert result.get("agent_outputs") is not None

    def test_graph_runs_with_simulated_multi_agent(self):
        cfg = AIOConfig(enable_priority_3=True)
        cfg.multi_agent.use_langgraph_backend = False
        app = build_aio_graph(cfg)
        state = make_initial_state("write a python function")
        state["intent"] = "coding"
        result = app.invoke(state)
        assert result["output"] is not None
        assert result.get("agent_outputs") is not None
