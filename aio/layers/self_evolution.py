from __future__ import annotations

import time
from typing import Any, Dict, List

from ..config.models import SelfEvolutionConfig
from .observability import ObservabilityLayer
from ..state import AIOState


class SelfEvolutionLayer:
    """Layer 9 — Analyzes performance trends and suggests safe, bounded config improvements.

    Args:
        config: Layer 9 configuration (window size, auto-apply flag).
        observability: Shared observability layer for spans and metrics.
    """

    def __init__(self, config: SelfEvolutionConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._snapshots: List[Dict[str, Any]] = []
        self._applied_deltas: List[Dict[str, Any]] = []

    def analyze(self, state: AIOState) -> AIOState:
        """Record a performance snapshot for the current turn.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``performance_snapshot``.
        """
        start = time.time()
        with self.obs.start_span("self_evolution.analyze", state.get("trace_id")):
            snapshot = {
                "turn": state.get("turn", 0),
                "latency_seconds": round(time.time() - start, 4),
                "success": state.get("error") is None and state.get("failure_state") == "HEALTHY",
                "memory_confidence": state.get("memory_confidence", 0.0),
                "verification_score": state.get("verification_result", {}).get("ensemble_score", 0.0),
            }
            self._snapshots.append(snapshot)
            state["performance_snapshot"] = snapshot
            self.obs.record_latency("self_evolution.analyze", time.time() - start)
            self.obs.count_node("self_evolution.analyze", "success")
        return state

    def generate_report(self, state: AIOState) -> AIOState:
        """Compute rolling averages and trends over the recent snapshot window.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``self_evolution_report``.
        """
        start = time.time()
        with self.obs.start_span("self_evolution.report", state.get("trace_id")):
            window = self._snapshots[-self.config.performance_window_size:]
            if not window:
                report = {"window_size": 0, "avg_latency": 0.0, "error_rate": 0.0, "memory_confidence_trend": "insufficient_data"}
            else:
                avg_latency = sum(s.get("latency_seconds", 0.0) for s in window) / len(window)
                error_rate = sum(1 for s in window if not s.get("success", True)) / len(window)
                mem_confidences = [s.get("memory_confidence", 0.0) for s in window]
                trend = "stable"
                if len(mem_confidences) >= 2:
                    first_half = sum(mem_confidences[:len(mem_confidences)//2]) / max(1, len(mem_confidences)//2)
                    second_half = sum(mem_confidences[len(mem_confidences)//2:]) / max(1, len(mem_confidences) - len(mem_confidences)//2)
                    if second_half > first_half + 0.1:
                        trend = "improving"
                    elif second_half < first_half - 0.1:
                        trend = "declining"
                report = {
                    "window_size": len(window),
                    "avg_latency": round(avg_latency, 4),
                    "error_rate": round(error_rate, 4),
                    "memory_confidence_trend": trend,
                }
            state["self_evolution_report"] = report
            self.obs.record_latency("self_evolution.report", time.time() - start)
            self.obs.count_node("self_evolution.report", "success")
        return state

    def suggest_improvements(self, state: AIOState) -> AIOState:
        """Propose safe config changes based on the latest report.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``suggested_config_delta``.
        """
        start = time.time()
        with self.obs.start_span("self_evolution.suggest", state.get("trace_id")):
            report = state.get("self_evolution_report", {})
            deltas: List[Dict[str, Any]] = []
            if report.get("memory_confidence_trend") == "declining":
                deltas.append({"key": "retrieval_top_k", "old": 5, "new": 7, "rationale": "Low memory confidence in window"})
            if report.get("error_rate", 0.0) > 0.3:
                deltas.append({"key": "base_backoff_seconds", "old": 1.0, "new": 2.0, "rationale": "High transient failure rate"})
            state["suggested_config_delta"] = deltas
            self.obs.record_latency("self_evolution.suggest", time.time() - start)
            self.obs.count_node("self_evolution.suggest", "success" if deltas else "none")
        return state

    def apply_deltas(self, state: AIOState) -> AIOState:
        """Apply whitelisted config deltas when ``auto_apply_config_delta`` is enabled.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``metrics["self_evolution_applied"]``.
        """
        start = time.time()
        with self.obs.start_span("self_evolution.apply", state.get("trace_id")):
            if not self.config.auto_apply_config_delta:
                self.obs.count_node("self_evolution.apply", "skipped")
                return state
            deltas = state.get("suggested_config_delta", [])
            applied = []
            whitelist = {"retrieval_top_k", "base_backoff_seconds", "max_tokens"}
            for delta in deltas:
                key = delta.get("key", "")
                if key in whitelist:
                    applied.append(delta)
                    self._applied_deltas.append(delta)
            state.setdefault("metrics", {})["self_evolution_applied"] = applied
            self.obs.record_latency("self_evolution.apply", time.time() - start)
            self.obs.count_node("self_evolution.apply", "success" if applied else "none")
        return state
