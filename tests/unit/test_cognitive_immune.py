import pytest
from unittest.mock import MagicMock, patch

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

    def test_learned_no_op_when_disabled(self, immune_layer):
        state = make_initial_state("test")
        state = immune_layer.scan(state)
        assert state.get("learned_anomaly_score") is None
        assert immune_layer._learning is None

    def test_learned_no_op_when_postgres_unavailable(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        cfg = CognitiveImmuneConfig(enable=True, learn_enable=True)
        layer = CognitiveImmuneSystem(cfg, obs)
        state = make_initial_state("test")
        state = layer.scan(state)
        assert state.get("learned_anomaly_score") == 0.0
        layer.close()

    def test_learned_zscore_boosts_anomaly(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        cfg = CognitiveImmuneConfig(
            enable=True,
            learn_enable=True,
            learn_z_threshold=2.0,
            learn_min_samples=5,
            learn_rolling_window=100,
        )
        layer = CognitiveImmuneSystem(cfg, obs)

        # Build a stable baseline
        baseline = []
        for _ in range(10):
            baseline.append((0, 0, 0))

        def _make_cursor(rows):
            cur = MagicMock()
            cur.fetchone.return_value = (0.0, 0.0, len(rows))
            return cur

        def _make_conn(rows):
            conn = MagicMock()
            conn.cursor.return_value.__enter__ = lambda s: _make_cursor(rows)
            conn.cursor.return_value.__exit__ = lambda s, *a: None
            return conn

        mock_conn = _make_conn(baseline)
        with patch.object(layer._learning, "_conn", mock_conn):
            state = make_initial_state("test")
            state["failure_count"] = 10
            state["safety_violations"] = []
            state["working_memory"] = []
            state = layer.scan(state)
            assert state["learned_anomaly_score"] > 0.0
            assert state["anomaly_score"] >= state["learned_anomaly_score"]
        layer.close()

    def test_learned_insufficient_samples_returns_zero(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        cfg = CognitiveImmuneConfig(
            enable=True,
            learn_enable=True,
            learn_min_samples=20,
            learn_rolling_window=100,
        )
        layer = CognitiveImmuneSystem(cfg, obs)

        def _make_cursor():
            cur = MagicMock()
            cur.fetchone.return_value = (0.0, 0.0, 5)
            return cur

        def _make_conn():
            conn = MagicMock()
            conn.cursor.return_value.__enter__ = lambda s: _make_cursor()
            conn.cursor.return_value.__exit__ = lambda s, *a: None
            return conn

        mock_conn = _make_conn()
        with patch.object(layer._learning, "_conn", mock_conn):
            state = make_initial_state("test")
            state["failure_count"] = 10
            state["safety_violations"] = []
            state["working_memory"] = []
            state = layer.scan(state)
            assert state["learned_anomaly_score"] == 0.0
        layer.close()
