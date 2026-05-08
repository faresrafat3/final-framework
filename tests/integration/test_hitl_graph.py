import pytest

from aio_framework import (
    AIOConfig,
    build_aio_graph,
    make_initial_state,
    HitlConfig,
)


class TestHitlGraphIntegration:
    def test_graph_routes_to_wait_on_destructive_plan(self):
        cfg = AIOConfig(hitl=HitlConfig(enable=True), enable_priority_3=True)
        graph = build_aio_graph(cfg)
        state = make_initial_state("delete all files")
        state["plan"] = "delete all files"
        result = graph.invoke(state)
        assert result.get("hitl_status") == "pending"
        assert result.get("execution_result") == {} or result.get("execution_result") is None

    def test_graph_proceeds_when_preapproved(self):
        cfg = AIOConfig(hitl=HitlConfig(enable=True), enable_priority_3=True)
        graph = build_aio_graph(cfg)
        state = make_initial_state("echo hello")
        state["plan"] = "echo hello"
        state["hitl_status"] = "approved"
        result = graph.invoke(state)
        assert result.get("execution_result") is not None
        assert result["execution_result"].get("tool") == "echo"

    def test_graph_escalates_when_rejected(self):
        cfg = AIOConfig(hitl=HitlConfig(enable=True), enable_priority_3=True)
        graph = build_aio_graph(cfg)
        state = make_initial_state("delete all files")
        state["plan"] = "delete all files"
        state["hitl_status"] = "rejected"
        result = graph.invoke(state)
        assert result.get("failure_state") == "FAILED"

    def test_post_finalize_escalation_on_immune_alert(self):
        cfg = AIOConfig(hitl=HitlConfig(enable=True), enable_priority_3=True)
        graph = build_aio_graph(cfg)
        state = make_initial_state("test")
        state["plan"] = "echo hello"
        state["hitl_status"] = "approved"
        state["immune_status"] = "ALERT"
        result = graph.invoke(state)
        assert result.get("escalation_reason") is not None
        assert "immune_alert" in result["escalation_reason"]

    def test_feedback_loop_injects_suggestions(self):
        cfg = AIOConfig(hitl=HitlConfig(enable=True, feedback_replay_max_corrections=5), enable_priority_3=True)
        graph = build_aio_graph(cfg)
        state = make_initial_state("test")
        state["plan"] = "echo hello"
        state["hitl_status"] = "approved"
        state["human_feedback"] = [{"intent": "general", "correction": "use python"}]
        result = graph.invoke(state)
        assert result.get("feedback_suggestions") is not None
