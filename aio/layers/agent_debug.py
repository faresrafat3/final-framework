from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, List, Optional

from ..config.models import AgentDebugConfig
from .observability import ObservabilityLayer
from ..state import AIOState


class AgentDebug:
    """Failure-analysis and prompt-optimization engine for Self-Evolution (Layer 9).

    Provides:
    * ``analyze_failure`` — root-cause classification from state traces.
    * ``generate_prompt_variants`` — A/B-ready prompt mutations.
    * ``ab_test`` — deterministic winner selection from variant scores.
    """

    def __init__(self, config: AgentDebugConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._failure_log: List[Dict[str, Any]] = []
        self._prompt_variant_history: List[Dict[str, Any]] = []

    def analyze_failure(self, state: AIOState) -> Dict[str, Any]:
        """Inspect state and produce a structured failure analysis.

        Returns a dict with keys: ``category``, ``confidence``, ``hypotheses``,
        ``recommended_action``.
        """
        start = time.time()
        with self.obs.start_span("agent_debug.analyze_failure", state.get("trace_id")):
            exec_res = state.get("execution_result", {})
            stderr = exec_res.get("stderr", "")
            exit_code = exec_res.get("exit_code", 0)
            ver = state.get("verification_result", {})
            failure_state = state.get("failure_state", "HEALTHY")

            category = "unknown"
            confidence = 0.5
            hypotheses: List[str] = []
            action = "none"

            if failure_state == "FAILED":
                if exit_code == 127 or "not found" in stderr.lower():
                    category = "missing_tool"
                    confidence = 0.9
                    hypotheses.append("Tool or command not found in registry.")
                    action = "register_fallback_tool"
                elif "permission" in stderr.lower():
                    category = "permission_denied"
                    confidence = 0.85
                    hypotheses.append("Insufficient permissions for requested operation.")
                    action = "escalate"
                elif not ver.get("passed", True):
                    category = "verification_failure"
                    confidence = 0.8
                    hypotheses.append("Plan failed ensemble verification.")
                    action = "replan"
                elif state.get("safety_violations"):
                    category = "safety_violation"
                    confidence = 0.95
                    hypotheses.append("NeuroShield or SemanticClassifier blocked execution.")
                    action = "reject"
                else:
                    category = "general_failure"
                    confidence = 0.6
                    hypotheses.append("Unclassified failure; review logs.")
                    action = "escalate"
            elif failure_state == "DEGRADED":
                category = "degraded"
                confidence = 0.7
                hypotheses.append("System is degraded but not failed; consider retry.")
                action = "retry"

            analysis = {
                "category": category,
                "confidence": round(confidence, 4),
                "hypotheses": hypotheses,
                "recommended_action": action,
                "timestamp": time.time(),
            }
            self._failure_log.append(analysis)
            self.obs.record_latency("agent_debug.analyze_failure", time.time() - start)
            self.obs.count_node("agent_debug.analyze_failure", category)
        return analysis

    def generate_prompt_variants(self, base_prompt: str, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate A/B-tested prompt variants from a base prompt.

        Each variant is a dict with ``variant_id``, ``prompt``, and ``mutation``.
        """
        start = time.time()
        with self.obs.start_span("agent_debug.generate_variants"):
            n = count or self.config.ab_variant_count
            variants: List[Dict[str, Any]] = []
            mutations = [
                lambda p: f"[STEP-BY-STEP] {p}",
                lambda p: f"[CONCISE] {p}",
                lambda p: f"[WITH EXAMPLES] {p}\nExample: echo hello -> prints hello",
                lambda p: p.replace("plan", "strategy"),
                lambda p: f"[SAFETY-FIRST] {p}\nRemember: never execute destructive commands.",
            ]
            for i in range(n):
                mut_fn = mutations[i % len(mutations)]
                variant = {
                    "variant_id": f"v{i}",
                    "prompt": mut_fn(base_prompt),
                    "mutation": mut_fn.__name__ if hasattr(mut_fn, "__name__") else "lambda",
                }
                variants.append(variant)
            self.obs.record_latency("agent_debug.generate_variants", time.time() - start)
            self.obs.count_node("agent_debug.generate_variants", "success")
        return variants

    def ab_test(self, variants: List[Dict[str, Any]], scores: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Run a deterministic A/B test and return the winning variant.

        If ``scores`` is not provided, synthetic deterministic scores are
        generated from the variant_id hash for reproducibility.
        """
        start = time.time()
        with self.obs.start_span("agent_debug.ab_test"):
            if not variants:
                return {"winner": None, "score": 0.0}

            if scores is None:
                scores = {}
                for v in variants:
                    # Deterministic pseudo-score from hash
                    h = hash(v["variant_id"]) % 1000 / 1000.0
                    scores[v["variant_id"]] = round(0.5 + h * 0.5, 4)

            winner_id = max(scores, key=lambda k: scores[k])
            winner_variant = next((v for v in variants if v["variant_id"] == winner_id), variants[0])
            result = {
                "winner": winner_variant,
                "winner_id": winner_id,
                "score": scores[winner_id],
                "all_scores": scores,
            }
            self._prompt_variant_history.append(result)
            self.obs.record_latency("agent_debug.ab_test", time.time() - start)
            self.obs.count_node("agent_debug.ab_test", "success")
        return result

    def run(self, state: AIOState) -> AIOState:
        """Full AgentDebug pipeline: analyze failure, generate variants, run A/B test."""
        start = time.time()
        with self.obs.start_span("agent_debug.run", state.get("trace_id")):
            analysis = self.analyze_failure(state)
            state["agent_debug_analysis"] = analysis

            base = state.get("plan", "") or state.get("raw_input", "")
            if base and self.config.enable_ab_testing:
                variants = self.generate_prompt_variants(base)
                ab_result = self.ab_test(variants)
                state["agent_debug_variants"] = variants
                state["agent_debug_ab_winner"] = ab_result
                # Optionally mutate plan with winning prompt
                if self.config.auto_apply_winner and ab_result["winner"]:
                    state["plan"] = ab_result["winner"]["prompt"]

            self.obs.record_latency("agent_debug.run", time.time() - start)
            self.obs.count_node("agent_debug.run", "success")
        return state
