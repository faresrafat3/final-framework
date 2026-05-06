import pytest

from aio_framework import (
    CognitiveImmuneSystem,
    CognitiveImmuneConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def immune_layer():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = CognitiveImmuneConfig(enable=True, auto_quarantine=True, auto_heal=True)
    return CognitiveImmuneSystem(cfg, obs)


class TestCognitiveImmuneSystem:
    def test_scan_healthy_state(self, immune_layer):
        state = make_initial_state("test")
        state = immune_layer.scan(state)
        assert state["anomaly_score"] == 0.0

    def test_scan_high_failure_count(self, immune_layer):
        state = make_initial_state("test")
        state["failure_count"] = 5
        state = immune_layer.scan(state)
        assert state["anomaly_score"] > 0.3

    def test_scan_corrupted_memory(self, immune_layer):
        state = make_initial_state("test")
        state["working_memory"] = [{"content": "ok"}, None, {"content": None}]
        state = immune_layer.scan(state)
        assert state["anomaly_score"] > 0.0

    def test_detect_threats_increments_counter(self, immune_layer):
        state = make_initial_state("test")
        state["failure_count"] = 5
        state = immune_layer.detect_threats(state)
        patterns = state["threat_patterns_detected"]
        rapid = next((p for p in patterns if p["pattern"] == "rapid_failure"), None)
        assert rapid is not None
        assert rapid["count"] >= 1

    def test_quarantine_captures_corrupted(self, immune_layer):
        state = make_initial_state("test")
        state["anomaly_score"] = 0.8
        state["working_memory"] = [{"id": "good", "content": "ok"}, None, {"id": "bad", "content": None}]
        state = immune_layer.quarantine(state)
        qids = state["quarantined_ids"]
        assert len(qids) == 2

    def test_quarantine_no_op_when_below_threshold(self, immune_layer):
        state = make_initial_state("test")
        state["anomaly_score"] = 0.1
        state["working_memory"] = [None]
        state = immune_layer.quarantine(state)
        assert state["quarantined_ids"] == []

    def test_heal_clears_corrupted(self, immune_layer):
        state = make_initial_state("test")
        state["failure_state"] = "HEALTHY"
        state["working_memory"] = [{"content": "ok"}, None, {"content": None}]
        state = immune_layer.heal(state)
        actions = state["healing_actions"]
        assert any(a["action"] == "clear_corrupted" for a in actions)
        assert len(state["working_memory"]) == 1

    def test_heal_blocked_when_failed(self, immune_layer):
        state = make_initial_state("test")
        state["failure_state"] = "FAILED"
        state = immune_layer.heal(state)
        actions = state["healing_actions"]
        assert any(a["action"] == "none" for a in actions)

    def test_heal_none_when_clean(self, immune_layer):
        state = make_initial_state("test")
        state["failure_state"] = "HEALTHY"
        state["working_memory"] = [{"content": "ok"}]
        state = immune_layer.heal(state)
        actions = state["healing_actions"]
        assert any(a["action"] == "none" for a in actions)

    def test_update_immunity_healthy(self, immune_layer):
        state = make_initial_state("test")
        state["anomaly_score"] = 0.0
        state = immune_layer.update_immunity(state)
        assert state["immune_status"] == "HEALTHY"

    def test_update_immunity_alert(self, immune_layer):
        state = make_initial_state("test")
        state["anomaly_score"] = 0.8
        state = immune_layer.update_immunity(state)
        assert state["immune_status"] == "ALERT"

    def test_threat_db_ttl_pruning(self, immune_layer):
        immune_layer._threat_db["old"] = {"count": 1, "first_seen": 0, "severity": "low"}
        state = make_initial_state("test")
        state = immune_layer.detect_threats(state)
        assert "old" not in immune_layer._threat_db
