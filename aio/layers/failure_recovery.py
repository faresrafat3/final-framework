from __future__ import annotations

import random
import re
import time
from enum import Enum
from typing import Any, Dict, List

from ..config.models import FailureRecoveryConfig
from .observability import ObservabilityLayer
from ..state import AIOState


class FailureState(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    FAILED = "FAILED"


class FailureRecovery:
    """ReCiSt state machine, NeuroShield, retry logic, anti-fragility learning."""

    def __init__(self, config: FailureRecoveryConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._failure_log: List[Dict[str, Any]] = []
        self._adaptive_thresholds: Dict[str, float] = {
            "retry_backoff_multiplier": 2.0,
            "escalation_score": 0.8,
        }

    def assess(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("failure.assess", state.get("trace_id")):
            exec_res = state.get("execution_result", {})
            err = exec_res.get("stderr", "")
            exit_code = exec_res.get("exit_code", 0)
            fstate = state.get("failure_state", "HEALTHY")
            fcount = state.get("failure_count", 0)
            budget = state.get("retry_budget", self.config.max_retries)

            classification = self._classify(err, exit_code)
            state["metrics"]["failure_classification"] = classification

            if classification == "transient":
                if fstate in ("HEALTHY", "RECOVERING"):
                    state["failure_state"] = "DEGRADED"
                state["failure_count"] = fcount + 1
                state["retry_budget"] = max(0, budget - 1)
            elif classification == "permanent":
                state["failure_state"] = "FAILED"
                state["failure_count"] = fcount + 1
                state["retry_budget"] = 0
            else:  # catastrophic
                state["failure_state"] = "FAILED"
                state["failure_count"] = fcount + 1
                state["retry_budget"] = 0
                state["error"] = f"Catastrophic failure: {err[:500]}"

            self.obs.set_failure_state(state["failure_state"])
            self._failure_log.append({
                "timestamp": time.time(),
                "classification": classification,
                "error": err,
                "state": state["failure_state"],
            })
            self.obs.record_latency("failure.assess", time.time() - start)
            self.obs.count_node("failure.assess", classification)
        return state

    def _classify(self, stderr: str, exit_code: int) -> str:
        lowered = stderr.lower()
        catastrophic_indicators = {"segfault", "killed", "out of memory", "panic", "catastrophic"}
        permanent_indicators = {"not found", "unknown tool", "no such file", "permission denied", "docker execution error"}
        if any(c in lowered for c in catastrophic_indicators) or exit_code == -9:
            return "catastrophic"
        if any(p in lowered for p in permanent_indicators) or exit_code == 127:
            return "permanent"
        return "transient"

    def retry(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("failure.retry", state.get("trace_id")):
            fcount = state.get("failure_count", 0)
            multiplier = self._adaptive_thresholds["retry_backoff_multiplier"]
            base = self.config.base_backoff_seconds
            max_backoff = self.config.max_backoff_seconds
            jitter = random.uniform(0, self.config.jitter_factor * base * (multiplier ** fcount))
            backoff = min(base * (multiplier ** fcount), max_backoff) + jitter
            state["metrics"]["retry_backoff_seconds"] = round(backoff, 3)
            self.obs.record_latency("failure.retry", time.time() - start)
            self.obs.count_node("failure.retry", "success")
        return state

    def shield(self, state: AIOState) -> AIOState:
        """NeuroShield: runtime safety boundary enforcement.

        Uses pattern matching and deterministic heuristics to intercept
        harmful, PII-leaking, system-integrity-violating, or jailbreak
        inputs. Sets ``failure_state`` to ``FAILED`` and populates
        ``safety_violations`` when threats are detected.
        """
        start = time.time()
        with self.obs.start_span("failure.shield", state.get("trace_id")):
            raw = state.get("raw_input", "")
            plan = state.get("plan", "")
            combined = f"{raw} {plan or ''}".lower()
            violations: List[Dict[str, Any]] = []
            patterns = {
                "harm": r"\b(kill|harm|attack|destroy)\b",
                "pii": r"\b(ssn|password|secret_key|api_key)\b",
                "system_integrity": r"(rm -rf /|mkfs|fdisk|drop table|delete from)",
            }
            for category, pattern in patterns.items():
                if re.search(pattern, combined):
                    violations.append({
                        "category": category,
                        "pattern": pattern,
                        "intercepted": True,
                        "timestamp": time.time(),
                    })
            if "override" in combined or "ignore previous" in combined:
                violations.append({
                    "category": "jailbreak",
                    "pattern": "override|ignore previous",
                    "intercepted": True,
                    "timestamp": time.time(),
                })

            if violations:
                state["safety_violations"] = state.get("safety_violations", []) + violations
                state["failure_state"] = "FAILED"
                state["error"] = f"NeuroShield intercepted {len(violations)} violation(s)."
                self.obs.set_failure_state("FAILED")
                self.obs.count_node("failure.shield", "blocked")
            else:
                self.obs.count_node("failure.shield", "allowed")
            self.obs.record_latency("failure.shield", time.time() - start)
        return state

    def learn(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("failure.learn", state.get("trace_id")):
            log = self._failure_log
            if len(log) >= 5:
                recent = log[-5:]
                transient_rate = sum(1 for r in recent if r["classification"] == "transient") / len(recent)
                if transient_rate > 0.8:
                    self._adaptive_thresholds["retry_backoff_multiplier"] = min(
                        3.0, self._adaptive_thresholds["retry_backoff_multiplier"] + 0.1
                    )
                else:
                    self._adaptive_thresholds["retry_backoff_multiplier"] = max(
                        1.0, self._adaptive_thresholds["retry_backoff_multiplier"] - 0.1
                    )
            state["metrics"]["adaptive_thresholds"] = dict(self._adaptive_thresholds)
            self.obs.record_latency("failure.learn", time.time() - start)
            self.obs.count_node("failure.learn", "success")
        return state

    def escalate(self, state: AIOState) -> AIOState:
        state["output"] = None
        state["error"] = state.get("error") or "Escalated to operator."
        state["failure_state"] = "FAILED"
        self.obs.set_failure_state("FAILED")
        self.obs.count_node("failure.escalate", "escalated")
        return state

    def degrade(self, state: AIOState) -> AIOState:
        state["output"] = state.get("output") or "[DEGRADED MODE] Limited response due to system failure."
        state["failure_state"] = "DEGRADED"
        self.obs.set_failure_state("DEGRADED")
        self.obs.count_node("failure.degrade", "degraded")
        return state
