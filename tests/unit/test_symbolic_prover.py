import pytest

from aio_framework import (
    SymbolicProver,
    SymbolicProverConfig,
    CausalGraphEngine,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def prover():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = SymbolicProverConfig(enable=True, enable_z3=False)
    return SymbolicProver(cfg, obs)


class TestCausalGraphEngine:
    def test_add_and_query(self):
        cg = CausalGraphEngine()
        cg.add_edge("A", "B", 0.9)
        cg.add_edge("B", "C", 0.8)
        paths = cg.find_paths("A", "C")
        assert len(paths) == 1
        assert paths[0] == ["A", "B", "C"]

    def test_cycle_detection(self):
        cg = CausalGraphEngine()
        cg.add_edge("A", "B")
        cg.add_edge("B", "C")
        cg.add_edge("C", "A")
        assert cg.has_cycle() is True

    def test_no_cycle(self):
        cg = CausalGraphEngine()
        cg.add_edge("A", "B")
        cg.add_edge("B", "C")
        assert cg.has_cycle() is False

    def test_backdoor_blocking(self):
        cg = CausalGraphEngine()
        cg.add_edge("X", "Y")
        cg.add_edge("Z", "X")
        cg.add_edge("Z", "Y")
        ok = cg.check_backdoor("X", "Y", {"Z"})
        assert ok is True


class TestSymbolicProver:
    def test_verify_plan_safety_heuristic_pass(self, prover):
        result = prover.verify_plan_safety("echo hello")
        assert result["passed"] is True
        assert result["method"] == "heuristic"

    def test_verify_plan_safety_heuristic_fail(self, prover):
        result = prover.verify_plan_safety("rm -rf /")
        assert result["passed"] is False
        assert "rm -rf /" in result["violations"]

    def test_verify_temporal_ordering_pass(self, prover):
        result = prover.verify_temporal_ordering(["a before b", "b before c"])
        assert result["passed"] is True

    def test_verify_temporal_ordering_fail(self, prover):
        result = prover.verify_temporal_ordering(["a before b", "b before a"])
        assert result["passed"] is False

    def test_verify_causal_graph(self, prover):
        prover.causal.add_edge("plan", "goal", 1.0)
        result = prover.verify_causal_graph("plan", "goal")
        assert result["passed"] is True
        assert result["cycle_free"] is True

    def test_prove_populates_state(self, prover):
        state = make_initial_state("test")
        state["plan"] = "1) step one 2) step two"
        state["neuro_symbolic_plan"] = {
            "steps": ["step one", "step two"],
            "relations": [{"source": "A", "target": "B", "confidence": 0.9}],
        }
        state = prover.prove(state)
        assert "symbolic_prover_result" in state
        assert state["symbolic_prover_result"]["overall_passed"] is True
