import pytest

from aio_framework import (
    Verifier,
    VerifierConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def verifier():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    return Verifier(VerifierConfig(ensemble_threshold=0.85), obs)


class TestVerifier:
    def test_critique_no_plan(self, verifier):
        state = make_initial_state("")
        state = verifier.critique(state)
        assert "No plan generated." in state["verification_result"]["critiques"]
        assert state["verification_result"]["llm_pass"] is False

    def test_critique_short_plan(self, verifier):
        state = make_initial_state("")
        state["plan"] = "x"
        state = verifier.critique(state)
        assert any("short" in c for c in state["verification_result"]["critiques"])

    def test_critique_valid_plan(self, verifier):
        state = make_initial_state("")
        state["plan"] = "Step 1: action A. Step 2: action B."
        state = verifier.critique(state)
        assert state["verification_result"]["llm_pass"] is True

    def test_judge_detects_forbidden_pattern(self, verifier):
        state = make_initial_state("")
        state["plan"] = "run rm -rf / now"
        state = verifier.judge(state)
        assert state["verification_result"]["formal_pass"] is False

    def test_judge_passes_clean_plan(self, verifier):
        state = make_initial_state("")
        state["plan"] = "print hello world"
        state = verifier.judge(state)
        assert state["verification_result"]["formal_pass"] is True

    def test_score_computes_ensemble(self, verifier):
        state = make_initial_state("")
        state["plan"] = "valid plan"
        state = verifier.critique(state)
        state = verifier.judge(state)
        state = verifier.score(state)
        score = state["verification_result"]["ensemble_score"]
        assert 0.0 <= score <= 1.0
        assert "passed" in state["verification_result"]

    def test_score_historical_trend(self, verifier):
        verifier._historical_scores = [0.9, 0.9, 0.9]
        state = make_initial_state("")
        state["plan"] = "valid plan"
        state = verifier.critique(state)
        state = verifier.judge(state)
        state = verifier.score(state)
        assert state["verification_result"]["ensemble_score"] > 0.0

    def test_debug_generates_hypotheses_on_failure(self, verifier):
        state = make_initial_state("")
        state["plan"] = ""
        state = verifier.critique(state)
        state = verifier.judge(state)
        state = verifier.score(state)
        state = verifier.debug(state)
        assert "debug_hypotheses" in state["verification_result"]
        assert len(state["verification_result"]["debug_hypotheses"]) > 0

    def test_debug_no_hypotheses_on_pass(self, verifier):
        state = make_initial_state("")
        state["plan"] = "Step 1: do something good."
        state = verifier.critique(state)
        state = verifier.judge(state)
        state = verifier.score(state)
        state = verifier.debug(state)
        assert state["verification_result"].get("debug_hypotheses") is None
