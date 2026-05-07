import pytest
from unittest.mock import MagicMock, patch

from aio_framework import (
    NeuroSymbolicMandate,
    NeuroSymbolicConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
    SymbolicEngine,
    SymbolicRule,
    KnowledgeGraph,
    FormalVerifier,
    ConstraintModel,
    SolverResult,
    SymbolicSolverBackend,
    NoOpBackend,
    NeuroSymbolicBridge,
    SymbolicPlanner,
    PlanVerifier,
)


@pytest.fixture
def ns_layer():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = NeuroSymbolicConfig(enable=True, enable_llm_parsing=False)
    return NeuroSymbolicMandate(cfg, obs)


@pytest.fixture
def obs():
    return ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))


class TestSymbolicRule:
    def test_rule_attributes(self):
        rule = SymbolicRule("test_rule", ["a", "b"], "c", weight=0.8)
        assert rule.name == "test_rule"
        assert rule.premises == ["a", "b"]
        assert rule.conclusion == "c"
        assert rule.weight == 0.8


class TestSymbolicEngine:
    def test_forward_chain_simple(self):
        engine = SymbolicEngine([
            SymbolicRule("r1", ["rain"], "wet"),
            SymbolicRule("r2", ["wet"], "slippery"),
        ])
        engine.add_fact("rain")
        result = engine.infer()
        assert "wet" in result["facts"]
        assert "slippery" in result["facts"]
        assert len(result["derived"]) == 2

    def test_no_progress_stops(self):
        engine = SymbolicEngine([
            SymbolicRule("r1", ["x"], "y"),
        ])
        engine.add_fact("a")
        result = engine.infer()
        assert "y" not in result["facts"]
        assert result["derived"] == []

    def test_max_depth_limits(self):
        engine = SymbolicEngine([
            SymbolicRule("r1", ["a"], "b"),
            SymbolicRule("r2", ["b"], "c"),
            SymbolicRule("r3", ["c"], "d"),
        ])
        engine.add_fact("a")
        result = engine.infer(max_depth=1)
        assert "a" in result["facts"]
        assert "b" in result["facts"]
        assert "c" not in result["facts"]
        assert "d" not in result["facts"]


class TestKnowledgeGraph:
    def test_add_and_query(self):
        kg = KnowledgeGraph()
        kg.add_entity("e1", "person", {"name": "Alice"})
        kg.add_entity("e2", "person", {"name": "Bob"})
        kg.add_relation("e1", "knows", "e2", confidence=0.9)
        results = kg.query("e1")
        assert len(results) == 1
        assert results[0]["relation"] == "knows"
        assert results[0]["target"] == "e2"

    def test_query_filter_by_relation(self):
        kg = KnowledgeGraph()
        kg.add_entity("e1", "person")
        kg.add_relation("e1", "knows", "e2")
        kg.add_relation("e1", "works_with", "e3")
        results = kg.query("e1", relation="knows")
        assert len(results) == 1
        assert results[0]["relation"] == "knows"

    def test_to_dict_roundtrip(self):
        kg = KnowledgeGraph()
        kg.add_entity("e1", "person")
        kg.add_relation("e1", "knows", "e2")
        d = kg.to_dict()
        assert "e1" in d["entities"]
        assert len(d["relations"]["e1"]) == 1


class TestFormalVerifier:
    def test_bounds_pass(self):
        cfg = NeuroSymbolicConfig(max_plan_length=100, max_inference_depth=5)
        fv = FormalVerifier(cfg)
        checks = fv.check_bounds("1) step one 2) step two")
        assert all(c["passed"] for c in checks)

    def test_bounds_fail_length(self):
        cfg = NeuroSymbolicConfig(max_plan_length=10, max_inference_depth=5)
        fv = FormalVerifier(cfg)
        checks = fv.check_bounds("this is a very long plan string")
        assert any(not c["passed"] and c["rule"] == "max_plan_length" for c in checks)

    def test_schema_pass(self):
        cfg = NeuroSymbolicConfig()
        fv = FormalVerifier(cfg)
        checks = fv.check_schema({"goal": "test", "steps": ["a"]})
        assert all(c["passed"] for c in checks)

    def test_schema_fail(self):
        cfg = NeuroSymbolicConfig()
        fv = FormalVerifier(cfg)
        checks = fv.check_schema({"steps": ["a"]})
        assert any(not c["passed"] and c["rule"] == "required_keys" for c in checks)

    def test_temporal_pass(self):
        cfg = NeuroSymbolicConfig()
        fv = FormalVerifier(cfg)
        checks = fv.check_temporal(["a", "b", "c"])
        assert all(c["passed"] for c in checks)

    def test_temporal_fail(self):
        cfg = NeuroSymbolicConfig()
        fv = FormalVerifier(cfg)
        checks = fv.check_temporal(["a before b", "b before a"])
        assert any(not c["passed"] and c["rule"] == "temporal_consistency" for c in checks)

    def test_verify_composite(self):
        cfg = NeuroSymbolicConfig(max_plan_length=100, max_inference_depth=5)
        fv = FormalVerifier(cfg)
        result = fv.verify("1) a 2) b", {"goal": "g", "steps": ["a", "b"]})
        assert result["passed"] is True
        assert len(result["checks"]) == 4


class TestNeuroSymbolicMandate:
    def test_parse_to_logic_heuristic(self, ns_layer):
        state = make_initial_state("test")
        state["plan"] = "1) step one 2) step two"
        state = ns_layer.parse_to_logic(state)
        sym = state["neuro_symbolic_plan"]
        assert sym["goal"] == "general"
        assert "step one" in sym["steps"]

    def test_infer_derives_facts(self, ns_layer):
        state = make_initial_state("test")
        state["plan"] = "plan has safety step"
        state["safety_violations"] = [{"type": "test"}]
        state = ns_layer.parse_to_logic(state)
        state = ns_layer.infer(state)
        inference = state["neuro_symbolic_inference"]
        assert "plan has safety step" in inference["facts"]
        assert any(d["conclusion"] == "plan is safe" for d in inference["derived"])

    def test_ground_knowledge_empty(self, ns_layer):
        state = make_initial_state("test")
        state["plan"] = "1) a"
        state = ns_layer.parse_to_logic(state)
        state = ns_layer.ground_knowledge(state)
        assert state["neuro_symbolic_grounding"] == []

    def test_verify_constraints_pass(self, ns_layer):
        state = make_initial_state("test")
        state["plan"] = "1) a 2) b"
        state = ns_layer.parse_to_logic(state)
        state = ns_layer.verify_constraints(state)
        assert state["neuro_symbolic_verdict"]["passed"] is True
        assert "neuro_symbolic_confidence" in state

    def test_verify_constraints_fail_length(self, ns_layer):
        cfg = NeuroSymbolicConfig(enable=True, enable_llm_parsing=False, max_plan_length=5)
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        layer = NeuroSymbolicMandate(cfg, obs)
        state = make_initial_state("test")
        state["plan"] = "this plan is way too long for the bound"
        state = layer.parse_to_logic(state)
        state = layer.verify_constraints(state)
        assert state["neuro_symbolic_verdict"]["passed"] is False
        assert state["neuro_symbolic_confidence"] < 1.0

    def test_synthesize_enriches_verification(self, ns_layer):
        state = make_initial_state("test")
        state["plan"] = "1) a"
        state = ns_layer.parse_to_logic(state)
        state = ns_layer.verify_constraints(state)
        state = ns_layer.synthesize(state)
        vresult = state["verification_result"]["neuro_symbolic"]
        assert "verdict" in vresult
        assert "inference" in vresult

    def test_synthesize_annotates_plan_on_failure(self):
        cfg = NeuroSymbolicConfig(enable=True, enable_llm_parsing=False, max_plan_length=5)
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        layer = NeuroSymbolicMandate(cfg, obs)
        state = make_initial_state("test")
        state["plan"] = "way too long plan string here"
        state = layer.parse_to_logic(state)
        state = layer.verify_constraints(state)
        state = layer.synthesize(state)
        assert "[NEURO-SYMBOLIC MITIGATION]" in state["plan"]

    def test_custom_rules_loaded(self):
        rules_json = '[{"name": "custom1", "premises": ["x"], "conclusion": "y", "weight": 0.5}]'
        cfg = NeuroSymbolicConfig(enable=True, enable_llm_parsing=False, custom_rules_json=rules_json)
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        layer = NeuroSymbolicMandate(cfg, obs)
        assert any(r.name == "custom1" for r in layer.engine.rules)

    def test_custom_rules_invalid_json_graceful(self):
        cfg = NeuroSymbolicConfig(enable=True, enable_llm_parsing=False, custom_rules_json="not-json")
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        layer = NeuroSymbolicMandate(cfg, obs)
        # Should not raise and default rules still present
        assert len(layer.engine.rules) >= 4


# ---------------------------------------------------------------------------
# Deep Neuro-Symbolic Integration — Priority 9
# ---------------------------------------------------------------------------

class TestSolverBackends:
    def test_noop_backend_returns_unknown(self):
        backend = NoOpBackend()
        result = backend.solve(ConstraintModel())
        assert result.status == "unknown"

    def test_z3_backend_sat(self):
        try:
            from aio.layers.neuro_symbolic import Z3Backend
        except Exception:
            pytest.skip("z3 not available")
        backend = Z3Backend()
        model = ConstraintModel(
            variables={"x": {"type": "int", "low": 0, "high": 10}},
            constraints=[{"type": "linear", "terms": {"x": 1}, "op": "<=", "rhs": 5}],
        )
        result = backend.solve(model, timeout_ms=5000)
        assert result.status == "sat"
        assert result.model is not None

    def test_z3_backend_unsat(self):
        try:
            from aio.layers.neuro_symbolic import Z3Backend
        except Exception:
            pytest.skip("z3 not available")
        backend = Z3Backend()
        model = ConstraintModel(
            variables={"x": {"type": "int", "low": 0, "high": 10}},
            constraints=[
                {"type": "linear", "terms": {"x": 1}, "op": ">=", "rhs": 20},
            ],
        )
        result = backend.solve(model, timeout_ms=5000)
        assert result.status == "unsat"

    def test_ortools_backend_sat(self):
        try:
            from aio.layers.neuro_symbolic import ORToolsBackend
        except Exception:
            pytest.skip("ortools not available")
        backend = ORToolsBackend()
        model = ConstraintModel(
            variables={"x": {"type": "int", "low": 0, "high": 10}},
            constraints=[{"type": "linear", "terms": {"x": 1}, "op": "<=", "rhs": 5}],
        )
        result = backend.solve(model, timeout_ms=5000)
        assert result.status == "sat"
        assert result.model is not None

    def test_ortools_backend_unsat(self):
        try:
            from aio.layers.neuro_symbolic import ORToolsBackend
        except Exception:
            pytest.skip("ortools not available")
        backend = ORToolsBackend()
        model = ConstraintModel(
            variables={"x": {"type": "int", "low": 0, "high": 10}},
            constraints=[
                {"type": "linear", "terms": {"x": 1}, "op": ">=", "rhs": 20},
            ],
        )
        result = backend.solve(model, timeout_ms=5000)
        assert result.status == "unsat"


class TestNeuroSymbolicBridge:
    def test_forward_from_plan(self, obs):
        cfg = NeuroSymbolicConfig(enable_symbolic_planning=True)
        bridge = NeuroSymbolicBridge(cfg, obs)
        state = make_initial_state("test")
        state["plan"] = "1) step one 2) step two"
        cm = bridge.forward(state)
        assert "step_count" in cm.variables
        assert any(c.get("type") == "linear" for c in cm.constraints)

    def test_forward_from_vmao_dag(self, obs):
        cfg = NeuroSymbolicConfig(enable_symbolic_planning=True)
        bridge = NeuroSymbolicBridge(cfg, obs)
        state = make_initial_state("test")
        state["vmao_dag"] = [
            {"id": "node-0", "description": "a", "dependencies": []},
            {"id": "node-1", "description": "b", "dependencies": ["node-0"]},
        ]
        cm = bridge.forward(state)
        assert "node-0" in cm.variables
        assert any(c.get("type") == "ordering" for c in cm.constraints)

    def test_backward_sat(self, obs):
        cfg = NeuroSymbolicConfig()
        bridge = NeuroSymbolicBridge(cfg, obs)
        result = SolverResult(status="sat", explanation="ok")
        text = bridge.backward(result)
        assert "passed" in text.lower()

    def test_backward_unsat(self, obs):
        cfg = NeuroSymbolicConfig()
        bridge = NeuroSymbolicBridge(cfg, obs)
        result = SolverResult(status="unsat", counterexample={"x": 10}, explanation="conflict")
        text = bridge.backward(result)
        assert "failed" in text.lower()


class TestSymbolicPlanner:
    def test_sat_path_marks_validated(self, obs):
        cfg = NeuroSymbolicConfig(enable_symbolic_planning=True)
        planner = SymbolicPlanner(cfg, obs)
        state = make_initial_state("test")
        state["plan"] = "1) step one 2) step two"
        state = planner.plan(state)
        assert state["symbolic_plan_validated"] is True
        assert state["symbolic_solver_result"]["status"] == "sat"

    def test_unsat_path_annotates_plan(self, obs):
        cfg = NeuroSymbolicConfig(enable_symbolic_planning=True, max_plan_length=5)
        planner = SymbolicPlanner(cfg, obs)
        state = make_initial_state("test")
        state["plan"] = "this plan is way too long for the bound"
        state = planner.plan(state)
        assert state["symbolic_plan_validated"] is False
        assert "[SYMBOLIC BLOCKED]" in state["plan"]

    def test_error_path_leaves_plan_unchanged(self, obs):
        cfg = NeuroSymbolicConfig(enable_symbolic_planning=True)
        planner = SymbolicPlanner(cfg, obs)
        # Force backend to raise
        planner.bridge.backend = MagicMock()
        planner.bridge.backend.solve.side_effect = RuntimeError("boom")
        state = make_initial_state("test")
        state["plan"] = "1) step"
        original_plan = state["plan"]
        state = planner.plan(state)
        assert state.get("plan") == original_plan


class TestPlanVerifier:
    def test_sat_verdict(self, obs):
        cfg = NeuroSymbolicConfig(enable_symbolic_planning=True)
        pv = PlanVerifier(cfg, obs)
        state = make_initial_state("test")
        state["plan"] = "1) step one 2) step two"
        verdict = pv.verify(state)
        assert verdict["satisfiable"] is True
        assert state["symbolic_verdict"] is not None

    def test_unsat_verdict(self, obs):
        cfg = NeuroSymbolicConfig(enable_symbolic_planning=True, max_plan_length=5)
        pv = PlanVerifier(cfg, obs)
        state = make_initial_state("test")
        state["plan"] = "this plan is way too long for the bound"
        verdict = pv.verify(state)
        assert verdict["satisfiable"] is False
        assert any(c["rule"] == "symbolic_satisfiability" and not c["passed"] for c in verdict["checks"])

    def test_counterexample_present_on_unsat(self, obs):
        cfg = NeuroSymbolicConfig(enable_symbolic_planning=True, max_plan_length=5)
        pv = PlanVerifier(cfg, obs)
        state = make_initial_state("test")
        state["plan"] = "this plan is way too long for the bound"
        verdict = pv.verify(state)
        assert "explanation" in verdict
