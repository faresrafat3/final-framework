from unittest.mock import MagicMock

import pytest

from aio_framework import (
    AIOConfig,
    build_aio_graph,
    make_initial_state,
    CognitiveImmuneSystem,
    CognitiveImmuneConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    MemoryBridge,
)


@pytest.fixture
def immune_deps():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = CognitiveImmuneConfig(enable=True, auto_quarantine=True, auto_heal=True)
    return {"obs": obs, "immune": CognitiveImmuneSystem(cfg, obs)}


class TestImmuneResponse:
    def test_memory_corruption_quarantine(self, immune_deps):
        immune = immune_deps["immune"]
        state = make_initial_state("test")
        state["anomaly_score"] = 0.8
        state["working_memory"] = [
            {"id": "e1", "content": "ok"},
            None,
            {"id": "e2", "content": None},
        ]
        state = immune.quarantine(state)
        assert len(state["quarantined_ids"]) == 2
        assert "e1" not in state["quarantined_ids"]

    def test_rapid_failure_escalation_detection(self, immune_deps):
        immune = immune_deps["immune"]
        state = make_initial_state("test")
        state["failure_count"] = 5
        state = immune.detect_threats(state)
        patterns = state["threat_patterns_detected"]
        rapid = next((p for p in patterns if p["pattern"] == "rapid_failure"), None)
        assert rapid is not None
        assert rapid["count"] >= 1
        assert rapid["severity"] == "high"

    def test_auto_heal_of_corrupted_working_memory(self, immune_deps):
        immune = immune_deps["immune"]
        state = make_initial_state("test")
        state["failure_state"] = "HEALTHY"
        state["working_memory"] = [{"content": "good"}, None, {"content": None}]
        state = immune.heal(state)
        assert len(state["working_memory"]) == 1
        assert state["working_memory"][0]["content"] == "good"

    def test_threat_pattern_persistence(self, immune_deps):
        immune = immune_deps["immune"]
        state = make_initial_state("test")
        state["failure_count"] = 5
        immune.detect_threats(state)
        immune.detect_threats(state)
        patterns = {p["pattern"]: p["count"] for p in state["threat_patterns_detected"]}
        assert patterns.get("rapid_failure", 0) >= 2

    def test_end_to_end_immune_response(self):
        cfg = AIOConfig(enable_priority_3=True)
        app = build_aio_graph(cfg)
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result.get("immune_status") is not None
        assert result.get("anomaly_score") is not None

    def test_immune_no_false_positive_on_clean_state(self, immune_deps):
        immune = immune_deps["immune"]
        state = make_initial_state("test")
        state["failure_state"] = "HEALTHY"
        state["failure_count"] = 0
        state["working_memory"] = [{"content": "clean"}]
        state = immune.scan(state)
        assert state["anomaly_score"] == 0.0
        state = immune.update_immunity(state)
        assert state["immune_status"] == "HEALTHY"
