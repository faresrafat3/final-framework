import pytest

from aio_framework import (
    SemanticClassifier,
    SemanticClassifierConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def classifier():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = SemanticClassifierConfig(enable=True, enable_llm=False)
    return SemanticClassifier(cfg, obs)


class TestSemanticClassifier:
    def test_regex_blocks_harm(self, classifier):
        result = classifier.classify("kill the process")
        assert result["overall_risk"] == "high"
        assert any(v["name"] == "harm" for v in result["violations"])

    def test_regex_blocks_pii(self, classifier):
        result = classifier.classify("my password is secret123")
        assert result["overall_risk"] == "high"
        assert any(v["name"] == "pii" for v in result["violations"])

    def test_regex_blocks_system_integrity(self, classifier):
        result = classifier.classify("drop table users")
        assert result["overall_risk"] == "critical"
        assert any(v["name"] == "system_integrity" for v in result["violations"])

    def test_safe_input_low_risk(self, classifier):
        result = classifier.classify("echo hello world")
        assert result["overall_risk"] == "low"
        assert result["violations"] == []

    def test_classify_state_blocks_and_mutates(self, classifier):
        state = make_initial_state("rm -rf /")
        state["plan"] = "destructive plan"
        state = classifier.classify_state(state)
        assert state["failure_state"] == "FAILED"
        assert "SemanticClassifier blocked" in state["error"]

    def test_custom_patterns_loaded(self):
        import json
        patterns = json.dumps([{"name": "custom", "pattern": "badword", "severity": "medium"}])
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        cfg = SemanticClassifierConfig(enable=True, enable_llm=False, custom_patterns_json=patterns)
        sc = SemanticClassifier(cfg, obs)
        result = sc.classify("this has badword in it")
        assert any(v["name"] == "custom" for v in result["violations"])

    def test_custom_patterns_invalid_json_graceful(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        cfg = SemanticClassifierConfig(enable=True, enable_llm=False, custom_patterns_json="not-json")
        sc = SemanticClassifier(cfg, obs)
        result = sc.classify("safe text")
        assert result["overall_risk"] == "low"
