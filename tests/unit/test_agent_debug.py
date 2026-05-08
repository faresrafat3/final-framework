import pytest

from aio_framework import (
    AgentDebug,
    AgentDebugConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def debug():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = AgentDebugConfig(enable=True, enable_ab_testing=True, ab_variant_count=3)
    return AgentDebug(cfg, obs)


class TestAgentDebug:
    def test_analyze_failure_missing_tool(self, debug):
        state = make_initial_state("")
        state["execution_result"] = {"stderr": "command not found", "exit_code": 127}
        state["failure_state"] = "FAILED"
        analysis = debug.analyze_failure(state)
        assert analysis["category"] == "missing_tool"
        assert analysis["recommended_action"] == "register_fallback_tool"

    def test_analyze_failure_permission_denied(self, debug):
        state = make_initial_state("")
        state["execution_result"] = {"stderr": "permission denied", "exit_code": 1}
        state["failure_state"] = "FAILED"
        analysis = debug.analyze_failure(state)
        assert analysis["category"] == "permission_denied"
        assert analysis["recommended_action"] == "escalate"

    def test_analyze_failure_verification(self, debug):
        state = make_initial_state("")
        state["execution_result"] = {"stderr": "", "exit_code": 0}
        state["failure_state"] = "FAILED"
        state["verification_result"] = {"passed": False}
        analysis = debug.analyze_failure(state)
        assert analysis["category"] == "verification_failure"

    def test_generate_prompt_variants(self, debug):
        variants = debug.generate_prompt_variants("base prompt", count=3)
        assert len(variants) == 3
        assert all("variant_id" in v for v in variants)

    def test_ab_test_selects_winner(self, debug):
        variants = debug.generate_prompt_variants("base", count=3)
        result = debug.ab_test(variants)
        assert result["winner"] is not None
        assert 0.0 <= result["score"] <= 1.0

    def test_run_populates_state(self, debug):
        state = make_initial_state("test")
        state["failure_state"] = "FAILED"
        state["plan"] = "do something"
        state = debug.run(state)
        assert "agent_debug_analysis" in state
        assert "agent_debug_variants" in state
        assert "agent_debug_ab_winner" in state
