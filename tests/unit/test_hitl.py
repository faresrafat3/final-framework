from unittest.mock import MagicMock

import pytest

from aio_framework import (
    HitlGate,
    FeedbackCollector,
    EscalationPolicy,
    FeedbackLoopEngine,
    HitlConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def obs():
    return ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))


@pytest.fixture
def hitl_gate_enabled(obs):
    return HitlGate(HitlConfig(enable=True), obs)


@pytest.fixture
def hitl_gate_disabled(obs):
    return HitlGate(HitlConfig(enable=False), obs)


@pytest.fixture
def feedback_collector(obs):
    return FeedbackCollector(HitlConfig(enable=True, feedback_replay_max_corrections=5), obs)


@pytest.fixture
def escalation_policy(obs):
    return EscalationPolicy(HitlConfig(enable=True), obs)


@pytest.fixture
def feedback_loop_engine(obs):
    return FeedbackLoopEngine(HitlConfig(enable=True, feedback_replay_max_corrections=5), obs)


class TestHitlGate:
    def test_disabled_pass_through(self, hitl_gate_disabled):
        state = make_initial_state("test")
        state = hitl_gate_disabled.check(state)
        assert state["hitl_status"] == "skipped"

    def test_non_destructive_plan(self, hitl_gate_enabled):
        state = make_initial_state("test")
        state["plan"] = "echo hello"
        state = hitl_gate_enabled.check(state)
        assert state["hitl_status"] == "non_destructive"

    def test_destructive_plan_pending(self, hitl_gate_enabled):
        state = make_initial_state("test")
        state["plan"] = "delete all files"
        state = hitl_gate_enabled.check(state)
        assert state["hitl_status"] == "pending"
        assert state["hitl_request"] is not None
        req = state["hitl_request"]
        assert req["status"] == "pending"
        assert "delete" in req["plan"].lower()

    def test_approved_status_passes_through(self, hitl_gate_enabled):
        state = make_initial_state("test")
        state["plan"] = "delete all files"
        state["hitl_status"] = "approved"
        state = hitl_gate_enabled.check(state)
        assert state["hitl_status"] == "approved"

    def test_rejected_status_passes_through(self, hitl_gate_enabled):
        state = make_initial_state("test")
        state["plan"] = "delete all files"
        state["hitl_status"] = "rejected"
        state = hitl_gate_enabled.check(state)
        assert state["hitl_status"] == "rejected"

    def test_approve_lifecycle(self, hitl_gate_enabled):
        state = make_initial_state("test")
        state["plan"] = "rm -rf /"
        state = hitl_gate_enabled.check(state)
        req_id = state["hitl_request"]["request_id"]
        assert hitl_gate_enabled.approve(req_id, "looks ok")
        pending = hitl_gate_enabled.get_pending()
        assert not any(r["request_id"] == req_id for r in pending)

    def test_reject_lifecycle(self, hitl_gate_enabled):
        state = make_initial_state("test")
        state["plan"] = "rm -rf /"
        state = hitl_gate_enabled.check(state)
        req_id = state["hitl_request"]["request_id"]
        assert hitl_gate_enabled.reject(req_id, "too dangerous")
        pending = hitl_gate_enabled.get_pending()
        assert not any(r["request_id"] == req_id for r in pending)

    def test_thread_safety_smoke(self, hitl_gate_enabled):
        import threading

        errors = []

        def worker():
            try:
                state = make_initial_state("test")
                state["plan"] = "drop database"
                hitl_gate_enabled.check(state)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(hitl_gate_enabled.get_pending()) == 20


class TestFeedbackCollector:
    def test_collect_appends_to_state(self, feedback_collector):
        state = make_initial_state("test")
        state["pending_feedback"] = {"correction": "use bash instead of python"}
        state = feedback_collector.collect(state)
        assert state["human_feedback"] is not None
        assert len(state["human_feedback"]) == 1
        assert state["pending_feedback"] is None

    def test_ingest_to_memory_calls_encode(self, feedback_collector):
        state = make_initial_state("test")
        state["human_feedback"] = [{"correction": "fix plan"}]
        mem = MagicMock()
        state = feedback_collector.ingest_to_memory(state, mem)
        mem.encode.assert_called_once()

    def test_ingest_graceful_when_mem_fails(self, feedback_collector):
        state = make_initial_state("test")
        state["human_feedback"] = [{"correction": "fix plan"}]
        mem = MagicMock()
        mem.encode.side_effect = RuntimeError("boom")
        state = feedback_collector.ingest_to_memory(state, mem)
        assert state.get("context_window") is not None


class TestEscalationPolicy:
    def test_escalates_on_safety_violation(self, escalation_policy):
        state = make_initial_state("test")
        state["safety_violations"] = [{"type": "test"}]
        state = escalation_policy.evaluate(state)
        assert state["escalation_reason"] == ["safety_violation"]
        assert state["failure_state"] == "FAILED"
        assert state["output"] is None
        assert "HITL escalation" in (state["error"] or "")

    def test_escalates_on_immune_alert(self, escalation_policy):
        state = make_initial_state("test")
        state["immune_status"] = "ALERT"
        state = escalation_policy.evaluate(state)
        assert "immune_alert" in (state["escalation_reason"] or [])

    def test_escalates_on_high_anomaly_score(self, escalation_policy):
        state = make_initial_state("test")
        state["anomaly_score"] = 0.9
        state = escalation_policy.evaluate(state)
        assert "immune_alert" in (state["escalation_reason"] or [])

    def test_clean_pass_through(self, escalation_policy):
        state = make_initial_state("test")
        state = escalation_policy.evaluate(state)
        assert state["escalation_reason"] is None
        assert state["failure_state"] == "HEALTHY"


class TestFeedbackLoopEngine:
    def test_replay_populates_suggestions(self, feedback_loop_engine):
        state = make_initial_state("test")
        state["intent"] = "coding"
        feedback_loop_engine.record_correction({"intent": "coding", "correction": "use type hints"})
        state = feedback_loop_engine.replay(state)
        assert state["feedback_suggestions"] is not None
        assert len(state["feedback_suggestions"]) == 1

    def test_replay_ignores_non_matching_intent(self, feedback_loop_engine):
        state = make_initial_state("test")
        state["intent"] = "general"
        feedback_loop_engine.record_correction({"intent": "coding", "correction": "use type hints"})
        state = feedback_loop_engine.replay(state)
        assert state["feedback_suggestions"] == []

    def test_replay_mutates_plan_when_planning_passed(self, feedback_loop_engine):
        state = make_initial_state("test")
        state["intent"] = "coding"
        state["plan"] = "original plan"
        feedback_loop_engine.record_correction({"intent": "coding", "correction": "add tests"})
        planning = MagicMock()
        state = feedback_loop_engine.replay(state, planning=planning)
        assert "[HUMAN_CORRECTION]" in (state["plan"] or "")

    def test_disabled_is_noop(self, obs):
        engine = FeedbackLoopEngine(HitlConfig(enable=False), obs)
        state = make_initial_state("test")
        state = engine.replay(state)
        assert state.get("feedback_suggestions") is None
