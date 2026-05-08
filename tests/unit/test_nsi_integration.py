import pytest

from aio_framework import (
    NSIIntegration,
    NSIIntegrationConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def nsi():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = NSIIntegrationConfig(enable=True)
    return NSIIntegration(cfg, obs)


class TestNSIIntegration:
    def test_lift_to_horn_extracts_steps(self, nsi):
        state = make_initial_state("test")
        state["neuro_symbolic_plan"] = {
            "steps": ["encode data", "verify integrity"],
            "relations": [],
        }
        state = nsi.lift_to_horn(state)
        clauses = state["nsi_horn_clauses"]
        assert any(c["head"] == "encode_data" for c in clauses)

    def test_lift_to_horn_extracts_relations(self, nsi):
        state = make_initial_state("test")
        state["neuro_symbolic_plan"] = {
            "steps": [],
            "relations": [{"source": "A", "target": "B", "confidence": 0.9}],
        }
        state = nsi.lift_to_horn(state)
        clauses = state["nsi_horn_clauses"]
        assert any(c["head"] == "b" and c["body"] == ["a"] for c in clauses)

    def test_forward_infer_derives_facts(self, nsi):
        state = make_initial_state("test")
        state["neuro_symbolic_plan"] = {
            "steps": ["rain"],
            "relations": [{"source": "rain", "target": "wet", "confidence": 1.0}],
        }
        state = nsi.lift_to_horn(state)
        state = nsi.forward_infer(state)
        facts = state["nsi_inferred_facts"]
        assert "wet" in facts

    def test_lift_back_enriches_plan(self, nsi):
        state = make_initial_state("test")
        state["neuro_symbolic_plan"] = {
            "steps": ["rain"],
            "relations": [{"source": "rain", "target": "wet", "confidence": 1.0}],
        }
        state = nsi.run(state)
        sym = state["neuro_symbolic_plan"]
        assert any(e["id"] == "rain" for e in sym["entities"])
        assert any(r.get("relation") == "implies" for r in sym["relations"])

    def test_run_idempotent(self, nsi):
        state = make_initial_state("test")
        state["neuro_symbolic_plan"] = {"steps": ["a"], "relations": []}
        state = nsi.run(state)
        first = state["nsi_horn_clauses"]
        state = nsi.run(state)
        second = state["nsi_horn_clauses"]
        assert len(second) >= len(first)
