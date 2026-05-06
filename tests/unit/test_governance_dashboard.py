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
