from unittest.mock import MagicMock, patch

import pytest

from aio_framework import (
    AIOConfig,
    build_aio_graph,
    make_initial_state,
    MemoryBridge,
    MemoryConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    ToolGate,
    FailureRecovery,
    Verifier,
    ContextManager,
)


@pytest.fixture
def chaos_deps():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = AIOConfig()
    return {
        "obs": obs,
        "mem": MemoryBridge(cfg.memory, obs),
        "toolgate": ToolGate(cfg.toolgate, obs),
        "recovery": FailureRecovery(cfg.failure_recovery, obs),
        "verifier": Verifier(cfg.verifier, obs),
        "ctx": ContextManager(cfg.context, obs),
    }


class TestChaosFailureInjection:
    def test_memory_corruption_recovery(self, chaos_deps):
        mem = chaos_deps["mem"]
        mem._episodic["bad"] = {"id": "bad", "content": None, "timestamp": 0}
        state = make_initial_state("")
        state = mem.verify(state)
        # Corrupted entry with None content should be handled
        assert "bad" not in mem._episodic or mem._episodic["bad"].get("verification_passed") is False

    def test_tool_timeout_simulation(self, chaos_deps):
        toolgate = chaos_deps["toolgate"]
        mock_container = MagicMock()
        mock_container.wait.side_effect = Exception("timeout")
        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container
        toolgate._docker_client = mock_client
        result = toolgate._docker_run(toolgate._registry["python_sandbox"], {"code": "print(1)"})
        assert result["success"] is False
        assert "timeout" in result["stderr"].lower() or "wait" in result["stderr"].lower()

    def test_docker_crash_graceful(self, chaos_deps):
        toolgate = chaos_deps["toolgate"]
        toolgate._docker_client = None
        result = toolgate._docker_run(toolgate._registry["bash_sandbox"], {"command": "echo hi"})
        assert result["success"] is False
        assert "Docker not available" in result["stderr"]

    def test_verification_failure_replan(self, chaos_deps):
        verifier = chaos_deps["verifier"]
        state = make_initial_state("")
        state["plan"] = ""
        state = verifier.critique(state)
        state = verifier.judge(state)
        state = verifier.score(state)
        assert state["verification_result"]["passed"] is False

    def test_context_overflow_with_massive_input(self, chaos_deps):
        ctx = chaos_deps["ctx"]
        state = make_initial_state("x" * 100000)
        state = ctx.ingest(state)
        state = ctx.sculpt(state)
        total = sum(
            ContextManager.approximate_token_count(str(m.get("content", "")))
            for m in state["context_window"]
        )
        assert total <= ctx.config.max_tokens - ctx.config.budget_reserve

    def test_constitutional_boundary_breach(self, chaos_deps):
        recovery = chaos_deps["recovery"]
        state = make_initial_state("drop table users")
        state = recovery.shield(state)
        cats = [v["category"] for v in state.get("safety_violations", [])]
        assert "system_integrity" in cats

    def test_retry_exhaustion_escalates(self, chaos_deps):
        recovery = chaos_deps["recovery"]
        state = make_initial_state("")
        state["execution_result"] = {"stderr": "connection reset", "exit_code": 1}
        state["retry_budget"] = 0
        state = recovery.assess(state)
        assert state["failure_state"] == "DEGRADED"  # or FAILED depending on state machine path

    def test_recovery_validates_state_transitions(self, chaos_deps):
        recovery = chaos_deps["recovery"]
        state = make_initial_state("")
        state["execution_result"] = {"stderr": "connection reset", "exit_code": 1}
        state = recovery.assess(state)
        assert state["failure_state"] in {"DEGRADED", "RECOVERING", "FAILED"}
        state = recovery.retry(state)
        assert "retry_backoff_seconds" in state["metrics"]

    def test_end_to_end_with_docker_unavailable(self):
        with patch("aio_framework.DOCKER_AVAILABLE", False):
            app = build_aio_graph(AIOConfig())
            state = make_initial_state("run python code: print(1)")
            result = app.invoke(state)
            assert result["output"] is not None or result["error"] is not None
