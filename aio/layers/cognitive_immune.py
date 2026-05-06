from __future__ import annotations

import time
from typing import Any, Dict, List

from ..config.models import CognitiveImmuneConfig
from .observability import ObservabilityLayer
from ..state import AIOState


class CognitiveImmuneSystem:
    """Anomaly detection, threat pattern tracking, quarantine, and self-healing."""

    def __init__(self, config: CognitiveImmuneConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._threat_db: Dict[str, Dict[str, Any]] = {}
        self._quarantine_store: Dict[str, Dict[str, Any]] = {}
        if config.learn_enable:
            from .immune_learning import ImmuneLearningEngine

            self._learning = ImmuneLearningEngine(config, observability)
        else:
            self._learning = None

    def scan(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("immune.scan", state.get("trace_id")):
            score = 0.0
            fcount = state.get("failure_count", 0)
            if fcount > 2:
                score += 0.4
            if state.get("retry_budget", 0) == 0 and state.get("failure_state") != "HEALTHY":
                score += 0.3
            violations = state.get("safety_violations", [])
            if len(violations) > 2:
                score += 0.3
            wm = state.get("working_memory", []) or []
            corrupted = sum(1 for m in wm if m is None or not isinstance(m, dict) or m.get("content") is None)
            if corrupted > 0:
                score += 0.2
            score = round(min(1.0, score), 4)
            if self._learning is not None:
                state["anomaly_score"] = score
                self._learning.record(state)
                learned = self._learning.compute_anomaly_score(state)
                score = max(score, learned)
                state["learned_anomaly_score"] = round(learned, 4)
            state["anomaly_score"] = round(min(1.0, score), 4)
            self.obs.record_latency("immune.scan", time.time() - start)
            self.obs.count_node("immune.scan", "success")
        return state

    def close(self) -> None:
        if self._learning is not None:
            self._learning.close()

    def detect_threats(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("immune.detect", state.get("trace_id")):
            now = time.time()
            ttl = self.config.pattern_db_ttl_seconds
            for key in list(self._threat_db.keys()):
                if now - self._threat_db[key].get("first_seen", now) > ttl:
                    del self._threat_db[key]
            if state.get("failure_count", 0) > 2:
                self._threat_db.setdefault("rapid_failure", {"count": 0, "first_seen": now, "severity": "high"})["count"] += 1
            wm = state.get("working_memory", []) or []
            corrupted = sum(1 for m in wm if m is None or not isinstance(m, dict) or m.get("content") is None)
            if corrupted > 0:
                self._threat_db.setdefault("memory_corruption", {"count": 0, "first_seen": now, "severity": "high"})["count"] += 1
            patterns = [{"pattern": k, "count": v["count"], "severity": v["severity"]} for k, v in self._threat_db.items()]
            state["threat_patterns_detected"] = patterns
            self.obs.record_latency("immune.detect", time.time() - start)
            self.obs.count_node("immune.detect", "success")
        return state

    def quarantine(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("immune.quarantine", state.get("trace_id")):
            qids: List[str] = []
            if self.config.auto_quarantine and state.get("anomaly_score", 0.0) > self.config.anomaly_threshold:
                wm = state.get("working_memory", []) or []
                for i, entry in enumerate(wm):
                    if entry is None or not isinstance(entry, dict) or entry.get("content") is None:
                        eid = entry.get("id", f"quarantine-{i}") if isinstance(entry, dict) else f"quarantine-{i}"
                        self._quarantine_store[eid] = {"entry": entry, "timestamp": time.time()}
                        qids.append(eid)
            state["quarantined_ids"] = qids
            self.obs.record_latency("immune.quarantine", time.time() - start)
            self.obs.count_node("immune.quarantine", "quarantined" if qids else "clean")
        return state

    def heal(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("immune.heal", state.get("trace_id")):
            actions: List[Dict[str, Any]] = []
            if not self.config.auto_heal:
                self.obs.count_node("immune.heal", "skipped")
                return state
            if state.get("failure_state") == "FAILED":
                actions.append({"action": "none", "target": "system", "rationale": "Auto-heal disabled when FAILED"})
                state["healing_actions"] = actions
                self.obs.record_latency("immune.heal", time.time() - start)
                self.obs.count_node("immune.heal", "blocked")
                return state
            wm = state.get("working_memory", []) or []
            cleaned = [m for m in wm if m is not None and isinstance(m, dict) and m.get("content") is not None]
            if len(cleaned) < len(wm):
                state["working_memory"] = cleaned
                actions.append({"action": "clear_corrupted", "target": "working_memory", "rationale": "Removed corrupted entries"})
            if state.get("failure_count", 0) > 0 and state.get("failure_state") == "HEALTHY":
                actions.append({"action": "reset_failure_counts", "target": "failure_state", "rationale": "State is healthy"})
            if not actions:
                actions.append({"action": "none", "target": "memory", "rationale": "No corruption detected"})
            state["healing_actions"] = actions
            self.obs.record_latency("immune.heal", time.time() - start)
            self.obs.count_node("immune.heal", "success" if any(a["action"] != "none" for a in actions) else "none")
        return state

    def update_immunity(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("immune.update", state.get("trace_id")):
            anomaly = state.get("anomaly_score", 0.0)
            if anomaly > self.config.anomaly_threshold:
                status = "ALERT"
            elif anomaly > 0.3:
                status = "WATCH"
            else:
                status = "HEALTHY"
            state["immune_status"] = status
            self.obs.record_latency("immune.update", time.time() - start)
            self.obs.count_node("immune.update", status.lower())
        return state
