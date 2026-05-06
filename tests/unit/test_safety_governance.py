import pytest

from aio_framework import (
    SafetyGovernance,
    SafetyGovernanceConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def gov_layer():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = SafetyGovernanceConfig(enable=True)
    return SafetyGovernance(cfg, obs)


class TestSafetyGovernance:
    def test_audit_records_trail(self, gov_layer):
        state = make_initial_state("test")
        state["turn"] = 2
        state["plan"] = "some plan"
        state["verification_result"] = {"passed": True}
        state = gov_layer.audit(state)
        trail = state["audit_trail"]
        assert len(trail) == 1
        assert trail[0]["turn"] == 2
        assert trail[0]["plan_present"] is True

    def test_audit_appends_multiple(self, gov_layer):
        state = make_initial_state("test")
        state = gov_layer.audit(state)
        state = gov_layer.audit(state)
        assert len(state["audit_trail"]) == 2

    def test_check_compliance_no_violations(self, gov_layer):
        state = make_initial_state("test")
        state["plan"] = "some plan"
        state["verification_result"] = {"passed": True}
        state = gov_layer.check_compliance(state)
        assert state["compliance_violations"] == []

    def test_check_compliance_pure_llm_detected(self, gov_layer):
        state = make_initial_state("test")
        state["plan"] = None
        state["verification_result"] = None
        state = gov_layer.check_compliance(state)
        violations = state["compliance_violations"]
        assert any(v["type"] == "pure_llm_decision" for v in violations)
        assert any(v["type"] == "uncritiqued_output" for v in violations)

    def test_governance_vote_blocked_when_violations(self, gov_layer):
        state = make_initial_state("test")
        state["compliance_violations"] = [{"type": "test"}]
        state = gov_layer.governance_vote(state)
        assert state["governance_result"]["vote_outcome"] == "blocked"

    def test_governance_vote_approved_when_clean(self, gov_layer):
        state = make_initial_state("test")
        state["compliance_violations"] = []
        state = gov_layer.governance_vote(state)
        assert state["governance_result"]["vote_outcome"] == "approved"
        assert state["governance_result"]["majority"] == 1.0

    def test_record_decision_appends(self, gov_layer):
        state = make_initial_state("test")
        state["governance_result"] = {"vote_outcome": "approved"}
        state["compliance_violations"] = []
        state = gov_layer.record_decision(state)
        assert len(gov_layer._decisions) == 1
