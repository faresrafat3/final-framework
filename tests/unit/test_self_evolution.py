import pytest

from aio_framework import (
    SelfEvolutionLayer,
    SelfEvolutionConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def se_layer():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = SelfEvolutionConfig(enable=True, auto_apply_config_delta=False)
    return SelfEvolutionLayer(cfg, obs)


class TestSelfEvolutionLayer:
    def test_analyze_records_snapshot(self, se_layer):
        state = make_initial_state("test")
        state["turn"] = 3
        state["memory_confidence"] = 0.8
        state["verification_result"] = {"ensemble_score": 0.9}
        state = se_layer.analyze(state)
        snap = state["performance_snapshot"]
        assert snap["turn"] == 3
        assert snap["success"] is True
        assert snap["memory_confidence"] == 0.8
        assert snap["verification_score"] == 0.9

    def test_generate_report_with_window(self, se_layer):
        state = make_initial_state("test")
        for i in range(3):
            state["turn"] = i + 1
            state = se_layer.analyze(state)
        state = se_layer.generate_report(state)
        report = state["self_evolution_report"]
        assert report["window_size"] == 3
        assert "avg_latency" in report
        assert "memory_confidence_trend" in report

    def test_suggest_improvements_declining_memory(self, se_layer):
        state = make_initial_state("test")
        se_layer._snapshots = [
            {"turn": 1, "memory_confidence": 0.9, "success": True, "latency_seconds": 0.1, "verification_score": 0.9},
            {"turn": 2, "memory_confidence": 0.5, "success": True, "latency_seconds": 0.1, "verification_score": 0.9},
            {"turn": 3, "memory_confidence": 0.3, "success": True, "latency_seconds": 0.1, "verification_score": 0.9},
        ]
        state["self_evolution_report"] = {
            "window_size": 3,
            "avg_latency": 0.1,
            "error_rate": 0.0,
            "memory_confidence_trend": "declining",
        }
        state = se_layer.suggest_improvements(state)
        deltas = state["suggested_config_delta"]
        assert any(d["key"] == "retrieval_top_k" for d in deltas)

    def test_suggest_improvements_high_error_rate(self, se_layer):
        state = make_initial_state("test")
        state["self_evolution_report"] = {
            "window_size": 3,
            "avg_latency": 0.1,
            "error_rate": 0.5,
            "memory_confidence_trend": "stable",
        }
        state = se_layer.suggest_improvements(state)
        deltas = state["suggested_config_delta"]
        assert any(d["key"] == "base_backoff_seconds" for d in deltas)

    def test_apply_deltas_skipped_when_disabled(self, se_layer):
        state = make_initial_state("test")
        state["suggested_config_delta"] = [{"key": "retrieval_top_k", "old": 5, "new": 7}]
        state = se_layer.apply_deltas(state)
        assert state["metrics"].get("self_evolution_applied") in ([], None)

    def test_apply_deltas_applies_whitelist(self, se_layer):
        se_layer.config.auto_apply_config_delta = True
        state = make_initial_state("test")
        state["suggested_config_delta"] = [
            {"key": "retrieval_top_k", "old": 5, "new": 7},
            {"key": "ensemble_threshold", "old": 0.85, "new": 0.8},
        ]
        state = se_layer.apply_deltas(state)
        applied = state["metrics"]["self_evolution_applied"]
        assert len(applied) == 1
        assert applied[0]["key"] == "retrieval_top_k"
