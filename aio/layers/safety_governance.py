from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ..config.models import SafetyGovernanceConfig
from .observability import ObservabilityLayer
from ..state import AIOState


class SafetyGovernance:
    """Per-turn audit, constitutional compliance, governance voting, and decision recording."""

    def __init__(
        self,
        config: SafetyGovernanceConfig,
        observability: ObservabilityLayer,
        store: Optional[Any] = None,
    ) -> None:
        self.config = config
        self.obs = observability
        self._store = store
        self._decisions: List[Dict[str, Any]] = []

    def audit(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("governance.audit", state.get("trace_id")):
            entry = {
                "turn": state.get("turn", 0),
                "timestamp": time.time(),
                "plan_present": bool(state.get("plan")),
                "verification_present": bool(state.get("verification_result")),
                "safety_clean": len(state.get("safety_violations", [])) == 0,
                "god_object_detected": self._detect_god_object(state),
            }
            trail = state.get("audit_trail", []) or []
            trail.append(entry)
            state["audit_trail"] = trail
            self.obs.record_latency("governance.audit", time.time() - start)
            self.obs.count_node("governance.audit", "success")
        return state

    def _detect_god_object(self, state: AIOState) -> bool:
        filled = sum(1 for v in state.values() if v is not None and v != [] and v != {} and v != 0 and v != 0.0 and v != "")
        total = len(state)
        return filled > 0 and (filled / total) > 0.9

    def check_compliance(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("governance.compliance", state.get("trace_id")):
            violations: List[Dict[str, Any]] = []
            if not state.get("plan"):
                violations.append({"type": "pure_llm_decision", "details": "No plan present in state"})
            if not state.get("verification_result"):
                violations.append({"type": "uncritiqued_output", "details": "No verification result in state"})
            if state.get("safety_violations"):
                violations.append({"type": "constitutional_breach", "details": "Safety violations detected"})
            if self._detect_god_object(state):
                violations.append({"type": "god_object", "details": "Single layer appears to dominate state"})
            state["compliance_violations"] = violations
            self.obs.record_latency("governance.compliance", time.time() - start)
            self.obs.count_node("governance.compliance", "success" if not violations else "violation")
        return state

    def governance_vote(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("governance.vote", state.get("trace_id")):
            violations = state.get("compliance_violations", []) or []
            if violations:
                outcome = "blocked"
                majority = 0.0
            else:
                outcome = "approved"
                majority = 1.0
            state["governance_result"] = {
                "sensitive_action": "none",
                "vote_outcome": outcome,
                "majority": majority,
            }
            self.obs.record_latency("governance.vote", time.time() - start)
            self.obs.count_node("governance.vote", outcome)
        return state

    def record_decision(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("governance.record", state.get("trace_id")):
            decision = {
                "turn": state.get("turn", 0),
                "timestamp": time.time(),
                "governance_result": state.get("governance_result"),
                "compliance_violations": state.get("compliance_violations"),
            }
            self._decisions.append(decision)
            if self._store is not None:
                sid = state.get("session_id") or "unknown"
                self._store.record_decision(sid, decision)
                self._store.ingest(state)
            self.obs.record_latency("governance.record", time.time() - start)
            self.obs.count_node("governance.record", "success")
        return state
