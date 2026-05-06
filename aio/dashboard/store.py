from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

from ..state import AIOState


class AuditStore:
    """Thread-safe in-memory store for governance audit trails and compliance violations.

    Integrates with :class:`aio.layers.safety_governance.SafetyGovernance` by
    accepting raw :class:`aio.state.AIOState` snapshots and extracting the
    ``audit_trail`` and ``compliance_violations`` fields.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: Dict[str, List[Dict[str, Any]]] = {}
        self._violations: Dict[str, List[Dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Write API — called by SafetyGovernance or background collectors
    # ------------------------------------------------------------------

    def ingest(self, state: AIOState) -> None:
        """Ingest a full AIOState snapshot and persist its governance data."""
        sid = state.get("session_id") or "unknown"
        turn = state.get("turn", 0)
        now = time.time()

        trail = state.get("audit_trail")
        if trail:
            for entry in trail:
                entry_copy = dict(entry)
                entry_copy.setdefault("session_id", sid)
                entry_copy.setdefault("turn", turn)
                entry_copy.setdefault("timestamp", now)
                self._add_audit_entry(sid, entry_copy)

        violations = state.get("compliance_violations")
        if violations:
            for v in violations:
                v_copy = dict(v)
                v_copy.setdefault("session_id", sid)
                v_copy.setdefault("turn", turn)
                v_copy.setdefault("timestamp", now)
                self._add_violation(sid, v_copy)

    def record_decision(self, session_id: str, decision: Dict[str, Any]) -> None:
        """Record a governance decision (used by SafetyGovernance.record_decision)."""
        decision_copy = dict(decision)
        decision_copy.setdefault("timestamp", time.time())
        self._add_audit_entry(session_id, decision_copy)

    # ------------------------------------------------------------------
    # Read API — used by the dashboard web UI
    # ------------------------------------------------------------------

    def get_sessions(self) -> List[str]:
        """Return all known session IDs."""
        with self._lock:
            return list(self._sessions.keys())

    def get_audit_trail(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return audit entries for a session (or all sessions if *None*)."""
        with self._lock:
            if session_id is None:
                results: List[Dict[str, Any]] = []
                for entries in self._sessions.values():
                    results.extend(entries)
                return results
            return list(self._sessions.get(session_id, []))

    def get_violations(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return compliance violations for a session (or all sessions if *None*)."""
        with self._lock:
            if session_id is None:
                results: List[Dict[str, Any]] = []
                for entries in self._violations.values():
                    results.extend(entries)
                return results
            return list(self._violations.get(session_id, []))

    def summary(self) -> Dict[str, Any]:
        """Return aggregate counts for the top-level dashboard view."""
        with self._lock:
            total_sessions = len(self._sessions)
            total_audits = sum(len(v) for v in self._sessions.values())
            total_violations = sum(len(v) for v in self._violations.values())
            violation_types: Dict[str, int] = {}
            for entries in self._violations.values():
                for e in entries:
                    vtype = e.get("type", "unknown")
                    violation_types[vtype] = violation_types.get(vtype, 0) + 1
            return {
                "total_sessions": total_sessions,
                "total_audits": total_audits,
                "total_violations": total_violations,
                "violation_types": violation_types,
            }

    def to_json(self, path: Optional[str] = None) -> str:
        """Serialize the full store to JSON.  If *path* is given, write to disk."""
        with self._lock:
            payload = {
                "sessions": {
                    sid: list(entries) for sid, entries in self._sessions.items()
                },
                "violations": {
                    sid: list(entries) for sid, entries in self._violations.items()
                },
            }
        raw = json.dumps(payload, indent=2, default=str)
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(raw)
        return raw

    def load_json(self, path: str) -> None:
        """Restore store contents from a JSON file written by :meth:`to_json`."""
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        with self._lock:
            self._sessions = {
                k: list(v) for k, v in payload.get("sessions", {}).items()
            }
            self._violations = {
                k: list(v) for k, v in payload.get("violations", {}).items()
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_audit_entry(self, session_id: str, entry: Dict[str, Any]) -> None:
        with self._lock:
            self._sessions.setdefault(session_id, []).append(entry)

    def _add_violation(self, session_id: str, entry: Dict[str, Any]) -> None:
        with self._lock:
            self._violations.setdefault(session_id, []).append(entry)
