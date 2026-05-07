import pytest
from unittest.mock import MagicMock, patch

from aio_framework import (
    Verifier,
    VerifierConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
    NeuroSymbolicConfig,
    PlanVerifier,
)


@pytest.fixture
def verifier():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    return Verifier(VerifierConfig(ensemble_threshold=0.85), obs)


@pytest.fixture
def verifier_with_symbolic():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    vcfg = VerifierConfig(ensemble_threshold=0.85, symbolic_judge_enabled=True)
    nscfg = NeuroSymbolicConfig(enable_symbolic_planning=True)
    return Verifier(vcfg, obs, neuro_symbolic_config=nscfg)


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


class TestVerifierSymbolicJudge:
    def test_judge_appends_symbolic_check(self, verifier_with_symbolic):
        state = make_initial_state("")
        state["plan"] = "1) step one 2) step two"
        state = verifier_with_symbolic.judge(state)
        checks = state["verification_result"]["formal_checks"]
        assert any(c["rule"] == "symbolic_satisfiability" for c in checks)

    def test_score_incorporates_symbolic_pass(self, verifier_with_symbolic):
        state = make_initial_state("")
        state["plan"] = "1) step one 2) step two"
        state = verifier_with_symbolic.critique(state)
        state = verifier_with_symbolic.judge(state)
        state = verifier_with_symbolic.score(state)
        score = state["verification_result"]["ensemble_score"]
        # With llm_pass=True, formal_pass=True, symbolic_pass=True,
        # ensemble should be high (>0.8 after blending)
        assert score > 0.8

    def test_score_incorporates_symbolic_fail(self, verifier_with_symbolic):
        state = make_initial_state("")
        state["plan"] = "1) step one 2) step two"
        state = verifier_with_symbolic.critique(state)
        state = verifier_with_symbolic.judge(state)
        # Force symbolic check to fail
        for c in state["verification_result"]["formal_checks"]:
            if c["rule"] == "symbolic_satisfiability":
                c["passed"] = False
        state = verifier_with_symbolic.score(state)
        score = state["verification_result"]["ensemble_score"]
        # Weighted reduction should still leave score above 0 because llm and formal pass
        assert 0.0 < score < 1.0

    def test_debug_adds_symbolic_hypothesis_on_failure(self, verifier_with_symbolic):
        state = make_initial_state("")
        state["plan"] = "1) step one 2) step two"
        state = verifier_with_symbolic.critique(state)
        state = verifier_with_symbolic.judge(state)
        for c in state["verification_result"]["formal_checks"]:
            if c["rule"] == "symbolic_satisfiability":
                c["passed"] = False
        state = verifier_with_symbolic.score(state)
        state = verifier_with_symbolic.debug(state)
        hypotheses = state["verification_result"].get("debug_hypotheses", [])
        assert any("symbolic" in h.lower() for h in hypotheses)

    def test_graceful_degradation_when_plan_verifier_raises(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        vcfg = VerifierConfig(ensemble_threshold=0.85, symbolic_judge_enabled=True)
        nscfg = NeuroSymbolicConfig(enable_symbolic_planning=True)
        verifier = Verifier(vcfg, obs, neuro_symbolic_config=nscfg)
        # Mock PlanVerifier to raise
        verifier._plan_verifier = MagicMock()
        verifier._plan_verifier.verify.side_effect = RuntimeError("solver crash")
        state = make_initial_state("")
        state["plan"] = "1) step"
        state = verifier.judge(state)
        checks = state["verification_result"]["formal_checks"]
        sym_check = next((c for c in checks if c["rule"] == "symbolic_satisfiability"), None)
        assert sym_check is not None
        assert sym_check["passed"] is False
        assert "error" in sym_check
