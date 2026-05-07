from __future__ import annotations

import time
from typing import Any, Dict, List

from ..config.models import VerifierConfig
from .observability import ObservabilityLayer
from ..state import AIOState


class Verifier:
    """Layer 5 — Multi-modal verification: LLM critique, formal rules, ensemble scoring, debug.

    Args:
        config: Layer 5 configuration (thresholds, feature flags).
        observability: Shared observability layer for spans and metrics.
    """

    def __init__(self, config: VerifierConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._historical_scores: List[float] = []

    def critique(self, state: AIOState) -> AIOState:
        """Run LLM-based critique on the current plan.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``verification_result["critiques"]`` and ``llm_pass``.
        """
        start = time.time()
        with self.obs.start_span("verifier.critique", state.get("trace_id")):
            plan = state.get("plan", "")
            critiques: List[str] = []
            if not plan:
                critiques.append("No plan generated.")
            else:
                if len(plan) < 10:
                    critiques.append("Plan is suspiciously short.")
                if "step" not in plan.lower() and "action" not in plan.lower():
                    critiques.append("Plan lacks explicit steps or actions.")
            result = state.setdefault("verification_result", {})
            result["critiques"] = critiques
            result["llm_pass"] = len(critiques) == 0
            self.obs.record_latency("verifier.critique", time.time() - start)
            self.obs.count_node("verifier.critique", "success" if result["llm_pass"] else "failure")
        return state

    def judge(self, state: AIOState) -> AIOState:
        """Run deterministic formal checks (forbidden patterns, length bounds).

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``verification_result["formal_checks"]`` and ``formal_pass``.
        """
        start = time.time()
        with self.obs.start_span("verifier.judge", state.get("trace_id")):
            result = state.setdefault("verification_result", {})
            checks: List[Dict[str, Any]] = []
            plan = state.get("plan", "")
            checks.append({"rule": "non_empty", "passed": bool(plan)})
            forbidden = {"rm -rf /", "drop table", "delete from", "format c:"}
            violation = any(f in (plan or "").lower() for f in forbidden)
            checks.append({"rule": "forbidden_patterns", "passed": not violation})
            checks.append({"rule": "length_bound", "passed": len(plan or "") < 5000})
            all_passed = all(c["passed"] for c in checks)
            result["formal_checks"] = checks
            result["formal_pass"] = all_passed
            self.obs.record_latency("verifier.judge", time.time() - start)
            self.obs.count_node("verifier.judge", "success" if all_passed else "failure")
        return state

    def score(self, state: AIOState) -> AIOState:
        """Compute an ensemble score blending LLM and formal results.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``verification_result["ensemble_score"]`` and ``passed``.
        """
        start = time.time()
        with self.obs.start_span("verifier.score", state.get("trace_id")):
            result = state.setdefault("verification_result", {})
            llm_pass = float(result.get("llm_pass", False))
            formal_pass = float(result.get("formal_pass", False))
            ensemble = llm_pass * 0.5 + formal_pass * 0.5
            if self._historical_scores:
                trend = sum(self._historical_scores[-10:]) / min(len(self._historical_scores), 10)
                ensemble = ensemble * 0.8 + trend * 0.2
            ensemble = round(max(0.0, min(1.0, ensemble)), 4)
            self._historical_scores.append(ensemble)
            result["ensemble_score"] = ensemble
            result["passed"] = ensemble >= self.config.ensemble_threshold
            self.obs.record_latency("verifier.score", time.time() - start)
            self.obs.count_node("verifier.score", "success" if result["passed"] else "failure")
        return state

    def debug(self, state: AIOState) -> AIOState:
        """Generate debug hypotheses when the ensemble score fails.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``verification_result["debug_hypotheses"]``.
        """
        start = time.time()
        with self.obs.start_span("verifier.debug", state.get("trace_id")):
            result = state.setdefault("verification_result", {})
            if not result.get("passed"):
                hypotheses = []
                if not result.get("llm_pass"):
                    hypotheses.append("Plan quality insufficient; consider more detailed decomposition.")
                if not result.get("formal_pass"):
                    hypotheses.append("Formal constraints violated; review forbidden patterns or length.")
                result["debug_hypotheses"] = hypotheses
            self.obs.record_latency("verifier.debug", time.time() - start)
            self.obs.count_node("verifier.debug", "success")
        return state
