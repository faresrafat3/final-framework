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
        self._hitl: Dict[str, List[Dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Write API — called by SafetyGovernance or background collectors
    # ------------------------------------------------------------------

    def ingest(self, state: AIOState) -> None:
        """Ingest a full AIOState snapshot and persist its governance data.

        Args:
            state: Current :class:`AIOState`.
        """
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
        """Record a governance decision (used by SafetyGovernance.record_decision).

        Args:
            session_id: Session identifier.
            decision: Decision dict to append.
        """
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
        """Return audit entries for a session (or all sessions if *None*).

        Args:
            session_id: Optional session filter.

        Returns:
            List of audit entry dicts.
        """
        with self._lock:
            if session_id is None:
                results: List[Dict[str, Any]] = []
                for entries in self._sessions.values():
                    results.extend(entries)
                return results
            return list(self._sessions.get(session_id, []))

    def get_violations(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return compliance violations for a session (or all sessions if *None*).

        Args:
            session_id: Optional session filter.

        Returns:
            List of violation dicts.
        """
        with self._lock:
            if session_id is None:
                results: List[Dict[str, Any]] = []
                for entries in self._violations.values():
                    results.extend(entries)
                return results
            return list(self._violations.get(session_id, []))

    def summary(self) -> Dict[str, Any]:
        """Return aggregate counts for the top-level dashboard view.

        Returns:
            Dict with ``total_sessions``, ``total_audits``, ``total_violations``,
            and ``violation_types``.
        """
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
        """Serialize the full store to JSON.  If *path* is given, write to disk.

        Args:
            path: Optional filesystem path.

        Returns:
            JSON string.
        """
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
        """Restore store contents from a JSON file written by :meth:`to_json`.

        Args:
            path: Filesystem path to a JSON snapshot.
        """
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

    # ------------------------------------------------------------------
    # HITL queue API
    # ------------------------------------------------------------------

    def record_hitl_request(self, session_id: str, request: Dict[str, Any]) -> None:
        """Record a HITL request into the in-memory queue.

        Args:
            session_id: Session identifier.
            request: HITL request dict (must contain ``request_id``).
        """
        with self._lock:
            self._hitl.setdefault(session_id, []).append(dict(request))

    def get_hitl_requests(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return HITL requests, optionally filtered by session and status.

        Args:
            session_id: Optional session filter.
            status: Optional status filter (``pending``, ``approved``, ``rejected``).

        Returns:
            List of matching HITL request dicts.
        """
        with self._lock:
            if session_id is None:
                results: List[Dict[str, Any]] = []
                for entries in self._hitl.values():
                    results.extend(entries)
            else:
                results = list(self._hitl.get(session_id, []))
        if status is not None:
            results = [r for r in results if r.get("status") == status]
        return results

    def update_hitl_request(
        self,
        session_id: str,
        request_id: str,
        status: str,
        comment: Optional[str] = None,
    ) -> bool:
        """Update the status of a HITL request.

        Args:
            session_id: Session identifier.
            request_id: The request UUID.
            status: New status (``approved`` or ``rejected``).
            comment: Optional operator comment.

        Returns:
            True if the request was found and updated.
        """
        with self._lock:
            for req in self._hitl.get(session_id, []):
                if req.get("request_id") == request_id:
                    req["status"] = status
                    if comment is not None:
                        req["comment"] = comment
                    return True
            return False
