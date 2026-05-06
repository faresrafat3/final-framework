import pytest

from aio_framework import build_aio_graph, AIOConfig, make_initial_state


class TestEndToEnd:
    def test_graph_compiles(self):
        app = build_aio_graph(AIOConfig())
        assert app is not None

    def test_echo_task(self):
        app = build_aio_graph(AIOConfig())
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result["output"] is not None
        assert result["error"] is None

    def test_safety_blocked_task(self):
        app = build_aio_graph(AIOConfig())
        state = make_initial_state("kill the process and rm -rf /")
        result = app.invoke(state)
        assert result["failure_state"] == "FAILED"
        assert len(result.get("safety_violations", [])) > 0

    def test_multi_turn_session(self):
        app = build_aio_graph(AIOConfig())
        sid = "session-123"
        for i in range(3):
            state = make_initial_state(f"turn {i}", session_id=sid)
            result = app.invoke(state)
            assert result["turn"] == 1  # each invoke is independent in this test

    def test_execution_failure_recovery_path(self):
        app = build_aio_graph(AIOConfig())
        # bash_sandbox with invalid command triggers failure path
        state = make_initial_state("run bash command: not_a_real_command_12345")
        result = app.invoke(state)
        # Should either recover and finalize or escalate
        assert result["output"] is not None or result["error"] is not None

    def test_context_overflow_handled(self):
        app = build_aio_graph(AIOConfig())
        long_input = "word " * 2000
        state = make_initial_state(long_input)
        result = app.invoke(state)
        # Should not crash; context was sculpted
        assert result["output"] is not None or result["error"] is not None
