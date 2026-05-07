import pytest

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
)


@pytest.fixture
def ns_layer():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = NeuroSymbolicConfig(enable=True, enable_llm_parsing=False)
    return NeuroSymbolicMandate(cfg, obs)


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
