import pytest
from unittest.mock import MagicMock, patch

from aio_framework import (
    PlanningLayer,
    PlanningConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
    LLMPlanner,
)


@pytest.fixture
def obs():
    return ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))


@pytest.fixture
def planning_disabled(obs):
    cfg = PlanningConfig(enable_llm_planning=False)
    return PlanningLayer(cfg, obs)


@pytest.fixture
def planning_enabled(obs):
    cfg = PlanningConfig(enable_llm_planning=True)
    return PlanningLayer(cfg, obs)


class TestLLMPlannerFallback:
    def test_llm_disabled_uses_heuristic(self, planning_disabled):
        state = make_initial_state("echo hello")
        state["intent"] = "action"
        state["working_memory"] = [{"content": "previous echo"}]
        state = planning_disabled.generate_plan(state)
        assert state["plan"] is not None
        assert "ingest input" in state["plan"]

    def test_llm_unavailable_uses_heuristic(self, planning_enabled):
        with patch("aio_framework.LANGCHAIN_CHAT_AVAILABLE", False):
            state = make_initial_state("echo hello")
            state["intent"] = "action"
            state = planning_enabled.generate_plan(state)
            assert state["plan"] is not None
            assert "ingest input" in state["plan"]

    def test_generate_plan_with_mocked_openai(self, planning_enabled):
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content="1) Step A\n2) Step B")
        with patch.object(planning_enabled._llm_planner, "_get_chat_model", return_value=mock_model):
            state = make_initial_state("run analysis")
            state["intent"] = "analysis"
            state["working_memory"] = [{"content": "memory snippet"}]
            state = planning_enabled.generate_plan(state)
            assert "Step A" in state["plan"]

    def test_decompose_tasks_json_parsing(self, planning_enabled):
        json_text = (
            '{"goal": "test", "subgoals": [{"id": "sg-1", "description": "d1", '
            '"actions": [{"id": "a1", "description": "act"}]}]}'
        )
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content=json_text)
        with patch.object(planning_enabled._llm_planner, "_get_chat_model", return_value=mock_model):
            state = make_initial_state("test")
            state["plan"] = "do something"
            state = planning_enabled.run_hiplan(state)
            assert state["hierarchical_plan"]["goal"] == "test"

    def test_lookahead_analysis_fallback_on_json_error(self, planning_enabled):
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content="not json")
        with patch.object(planning_enabled._llm_planner, "_get_chat_model", return_value=mock_model):
            state = make_initial_state("test")
            state["plan"] = "do something"
            state = planning_enabled.run_flare(state)
            assert "trajectory_scores" in state["lookahead_result"]

    def test_pitfall_analysis_llm_blocked(self, planning_enabled):
        json_text = (
            '{"pitfalls_detected": [{"type": "unsafe", "mitigation": "stop"}], '
            '"guardrails_added": ["stop"], "safe_to_proceed": false}'
        )
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content=json_text)
        with patch.object(planning_enabled._llm_planner, "_get_chat_model", return_value=mock_model):
            state = make_initial_state("test")
            state["plan"] = "do something"
            state = planning_enabled.run_ppa(state)
            assert state["pitfall_analysis"]["safe_to_proceed"] is False
            assert state["failure_state"] == "FAILED"

    def test_planning_layer_observability_counts(self, planning_enabled):
        mock_model = MagicMock()
        mock_model.invoke.side_effect = RuntimeError("boom")
        with patch.object(planning_enabled._llm_planner, "_get_chat_model", return_value=mock_model):
            with patch.object(planning_enabled.obs, "count_node") as mock_count:
                state = make_initial_state("test")
                state["plan"] = "do something"
                state = planning_enabled.run_flare(state)
                mock_count.assert_any_call("planning.llm_lookahead", "fallback")

    def test_llm_planner_parse_json_strip_fences(self):
        text = '```json\n{"a": 1}\n```'
        result = LLMPlanner._parse_json(text)
        assert result == {"a": 1}

    def test_llm_planner_parse_json_invalid_returns_empty(self):
        result = LLMPlanner._parse_json("not json")
        assert result == {}

    def test_generate_plan_records_latency_and_count(self, planning_enabled):
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content="1) step")
        with patch.object(planning_enabled._llm_planner, "_get_chat_model", return_value=mock_model):
            with patch.object(planning_enabled.obs, "record_latency") as mock_lat:
                with patch.object(planning_enabled.obs, "count_node") as mock_count:
                    state = make_initial_state("test")
                    state = planning_enabled.generate_plan(state)
                    mock_lat.assert_called()
                    mock_count.assert_called()
