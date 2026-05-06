import json
import os
import tempfile

import pytest

from aio_framework import AuditStore, make_initial_state


class TestAuditStore:
    def test_ingest_extracts_audit_trail_and_violations(self):
        store = AuditStore()
        state = make_initial_state("test")
        state["session_id"] = "s1"
        state["turn"] = 1
        state["audit_trail"] = [{"turn": 1, "plan_present": True}]
        state["compliance_violations"] = [{"type": "pure_llm_decision", "details": "no plan"}]
        store.ingest(state)

        assert store.get_sessions() == ["s1"]
        assert len(store.get_audit_trail("s1")) == 1
        assert len(store.get_violations("s1")) == 1

    def test_summary_counts(self):
        store = AuditStore()
        state = make_initial_state("test")
        state["session_id"] = "s2"
        state["audit_trail"] = [{"turn": 0}]
        state["compliance_violations"] = [{"type": "x"}, {"type": "x"}]
        store.ingest(state)

        summary = store.summary()
        assert summary["total_sessions"] == 1
        assert summary["total_audits"] == 1
        assert summary["total_violations"] == 2
        assert summary["violation_types"] == {"x": 2}

    def test_record_decision(self):
        store = AuditStore()
        store.record_decision("s3", {"turn": 5, "governance_result": "approved"})
        audits = store.get_audit_trail("s3")
        assert len(audits) == 1
        assert audits[0]["governance_result"] == "approved"

    def test_to_json_and_load_json(self):
        store = AuditStore()
        store.record_decision("s4", {"turn": 1})
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
            path = fh.name
        try:
            raw = store.to_json(path)
            assert "s4" in raw

            store2 = AuditStore()
            store2.load_json(path)
            assert store2.get_sessions() == ["s4"]
        finally:
            os.remove(path)

    def test_get_all_audits_when_session_id_none(self):
        store = AuditStore()
        state = make_initial_state("test")
        state["session_id"] = "s5"
        state["audit_trail"] = [{"turn": 1}]
        store.ingest(state)
        all_audits = store.get_audit_trail(None)
        assert len(all_audits) == 1

    def test_load_missing_file_is_noop(self):
        store = AuditStore()
        store.load_json("/nonexistent/path/audit.json")
        assert store.get_sessions() == []
