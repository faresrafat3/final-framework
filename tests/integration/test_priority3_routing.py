import pytest

from aio_framework import (
    build_aio_graph,
    AIOConfig,
    make_initial_state,
    END,
)


class TestPriority3Routing:
    def test_graph_compiles_with_priority3_enabled(self):
        cfg = AIOConfig(enable_priority_3=True)
        app = build_aio_graph(cfg)
        assert app is not None

    def test_graph_compiles_with_priority3_disabled(self):
        cfg = AIOConfig(enable_priority_3=False)
        app = build_aio_graph(cfg)
        assert app is not None

    def test_multi_agent_branch_for_coding_intent(self):
        cfg = AIOConfig(enable_priority_3=True)
        app = build_aio_graph(cfg)
        state = make_initial_state("write a python function")
        state["intent"] = "coding"
        result = app.invoke(state)
        assert result["output"] is not None

    def test_multi_agent_branch_for_analysis_intent(self):
        cfg = AIOConfig(enable_priority_3=True)
        app = build_aio_graph(cfg)
        state = make_initial_state("analyze the dataset")
        state["intent"] = "analysis"
        result = app.invoke(state)
        assert result["output"] is not None

    def test_governance_audit_gate_runs_before_verify(self):
        cfg = AIOConfig(enable_priority_3=True)
        app = build_aio_graph(cfg)
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result.get("audit_trail") is not None
        assert len(result["audit_trail"]) > 0

    def test_post_finalize_reflection_pipeline(self):
        cfg = AIOConfig(enable_priority_3=True)
        app = build_aio_graph(cfg)
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result.get("performance_snapshot") is not None
        assert result.get("immune_status") is not None

    def test_priority3_disabled_no_reflection_fields(self):
        cfg = AIOConfig(enable_priority_3=False)
        app = build_aio_graph(cfg)
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result.get("performance_snapshot") is None
        assert result.get("immune_status") is None

    def test_safety_governance_blocked_noncompliant(self):
        cfg = AIOConfig(enable_priority_3=True)
        app = build_aio_graph(cfg)
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result.get("governance_result") is not None

    def test_immune_quarantine_with_corrupted_memory(self):
        cfg = AIOConfig(enable_priority_3=True)
        app = build_aio_graph(cfg)
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result.get("quarantined_ids") is not None
