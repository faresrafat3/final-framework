import os
from unittest.mock import MagicMock

import pytest

from aio_framework import (
    AuditStore,
    create_dashboard_app,
    GovernanceDashboardConfig,
    SafetyGovernance,
    SafetyGovernanceConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None


class TestGovernanceDashboardApp:
    @pytest.fixture
    def client(self):
        if TestClient is None:
            pytest.skip("fastapi not installed")
        store = AuditStore()
        app = create_dashboard_app(store)
        return TestClient(app)

    def test_index_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "AIO Governance Dashboard" in response.text

    def test_session_detail_html(self, client):
        response = client.get("/session/test-session")
        assert response.status_code == 200
        assert "test-session" in response.text

    def test_api_summary(self, client):
        response = client.get("/api/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 0

    def test_api_audits_and_violations(self, client):
        client.get("/api/audits").json() == []
        client.get("/api/violations").json() == []

    def test_api_audits_with_session_filter(self, client):
        store = AuditStore()
        state = make_initial_state("hello")
        state["session_id"] = "s1"
        state["audit_trail"] = [{"turn": 1, "plan_present": True}]
        store.ingest(state)
        app = create_dashboard_app(store)
        c = TestClient(app)
        resp = c.get("/api/audits?session_id=s1")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestSafetyGovernanceStoreIntegration:
    def test_record_decision_persists_to_store(self):
        store = AuditStore()
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        gov = SafetyGovernance(SafetyGovernanceConfig(enable=True), obs, store=store)
        state = make_initial_state("test")
        state["session_id"] = "s1"
        state["turn"] = 2
        state["governance_result"] = {"vote_outcome": "approved"}
        state["compliance_violations"] = []
        gov.record_decision(state)

        assert "s1" in store.get_sessions()
        assert len(store.get_audit_trail("s1")) >= 1

    def test_governance_without_store_does_not_crash(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        gov = SafetyGovernance(SafetyGovernanceConfig(enable=True), obs, store=None)
        state = make_initial_state("test")
        state["governance_result"] = {"vote_outcome": "approved"}
        state["compliance_violations"] = []
        result = gov.record_decision(state)
        assert result["governance_result"]["vote_outcome"] == "approved"


class TestGovernanceDashboardHitl:
    def test_hitl_html_renders(self, client):
        response = client.get("/hitl")
        assert response.status_code == 200
        assert "HITL Review Queue" in response.text

    def test_api_hitl_list_and_filter(self, client):
        store = AuditStore()
        store.record_hitl_request("s1", {"request_id": "r1", "status": "pending", "plan": "drop table"})
        store.record_hitl_request("s1", {"request_id": "r2", "status": "approved", "plan": "echo"})
        app = create_dashboard_app(store)
        c = TestClient(app)
        all_reqs = c.get("/api/hitl").json()
        assert len(all_reqs) == 2
        pending = c.get("/api/hitl?status=pending").json()
        assert len(pending) == 1
        assert pending[0]["request_id"] == "r1"

    def test_api_hitl_approve_reject(self, client):
        store = AuditStore()
        store.record_hitl_request("s1", {"request_id": "r1", "status": "pending", "plan": "drop"})
        app = create_dashboard_app(store)
        c = TestClient(app)
        resp = c.post("/api/hitl", json={"session_id": "s1", "request_id": "r1", "action": "approve", "comment": "ok"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        reqs = c.get("/api/hitl?status=approved").json()
        assert len(reqs) == 1
        resp2 = c.post("/api/hitl", json={"session_id": "s1", "request_id": "r1", "action": "reject"})
        assert resp2.json()["success"] is True


class TestGovernanceDashboardConfig:
    def test_default_disable(self):
        cfg = GovernanceDashboardConfig()
        assert cfg.enable is False

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("GOVERNANCE_DASHBOARD_ENABLE", "true")
        monkeypatch.setenv("GOVERNANCE_DASHBOARD_PORT", "9090")
        cfg = GovernanceDashboardConfig()
        assert cfg.enable is True
        assert cfg.port == 9090
