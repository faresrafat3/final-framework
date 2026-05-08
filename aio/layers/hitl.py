from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from ..config.models import HitlConfig
from .observability import ObservabilityLayer
from ..state import AIOState


logger = logging.getLogger(__name__)


class HitlGate:
    """Layer 9 — Human-in-the-Loop gate that interrupts execution before destructive actions.

    Args:
        config: HITL configuration (enable flag, destructive patterns, timeout).
        observability: Shared observability layer for spans and metrics.
    """

    def __init__(self, config: HitlConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _is_destructive(self, plan: Optional[str]) -> bool:
        if not plan:
            return False
        lowered = plan.lower()
        for pattern in self.config.destructive_patterns:
            if re.search(pattern, lowered):
                return True
        return False

    def check(self, state: AIOState) -> AIOState:
        """Evaluate whether the current plan requires human approval.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``hitl_status`` and ``hitl_request``.
        """
        start = time.time()
        with self.obs.start_span("hitl.check", state.get("trace_id")):
            if not self.config.enable:
                state["hitl_status"] = "skipped"
                self.obs.record_latency("hitl.check", time.time() - start)
                self.obs.count_node("hitl.check", "skipped")
                return state

            existing_status = state.get("hitl_status")
            if existing_status == "approved":
                self.obs.record_latency("hitl.check", time.time() - start)
                self.obs.count_node("hitl.check", "approved")
                return state
            if existing_status == "rejected":
                state["hitl_status"] = "rejected"
                self.obs.record_latency("hitl.check", time.time() - start)
                self.obs.count_node("hitl.check", "rejected")
                return state

            plan = state.get("plan") or ""
            if not self._is_destructive(plan):
                state["hitl_status"] = "non_destructive"
                self.obs.record_latency("hitl.check", time.time() - start)
                self.obs.count_node("hitl.check", "non_destructive")
                return state

            req_id = str(uuid.uuid4())
            request = {
                "request_id": req_id,
                "session_id": state.get("session_id", "unknown"),
                "turn": state.get("turn", 0),
                "plan": plan,
                "status": "pending",
                "timestamp": time.time(),
            }
            with self._lock:
                self._pending[req_id] = request
            state["hitl_status"] = "pending"
            state["hitl_request"] = request
            self.obs.record_latency("hitl.check", time.time() - start)
            self.obs.count_node("hitl.check", "pending")
        return state

    def approve(self, request_id: str, comment: Optional[str] = None) -> bool:
        """Approve a pending HITL request.

        Args:
            request_id: The UUID of the pending request.
            comment: Optional operator comment.

        Returns:
            True if the request was found and approved.
        """
        with self._lock:
            req = self._pending.get(request_id)
            if req is None:
                return False
            req["status"] = "approved"
            req["comment"] = comment
            return True

    def reject(self, request_id: str, comment: Optional[str] = None) -> bool:
        """Reject a pending HITL request.

        Args:
            request_id: The UUID of the pending request.
            comment: Optional operator comment.

        Returns:
            True if the request was found and rejected.
        """
        with self._lock:
            req = self._pending.get(request_id)
            if req is None:
                return False
            req["status"] = "rejected"
            req["comment"] = comment
            return True

    def get_pending(self) -> List[Dict[str, Any]]:
        """Return all requests currently awaiting approval."""
        with self._lock:
            return [dict(r) for r in self._pending.values() if r.get("status") == "pending"]


class FeedbackCollector:
    """Collects structured human feedback and ingests it into MemoryBridge.

    Args:
        config: HITL configuration.
        observability: Shared observability layer.
    """

    def __init__(self, config: HitlConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    def collect(self, state: AIOState) -> AIOState:
        """Append any pending feedback to the state's human_feedback log.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``human_feedback`` extended.
        """
        start = time.time()
        with self.obs.start_span("hitl.feedback_collect", state.get("trace_id")):
            feedback = state.get("pending_feedback")
            if feedback:
                log = state.get("human_feedback") or []
                log.append(feedback)
                state["human_feedback"] = log
                state["pending_feedback"] = None
            self.obs.record_latency("hitl.feedback_collect", time.time() - start)
            self.obs.count_node("hitl.feedback_collect", "success")
        return state

    def ingest_to_memory(self, state: AIOState, mem: Any) -> AIOState:
        """Create synthetic context-window entries from human feedback and encode them.

        Args:
            state: Current :class:`AIOState`.
            mem: :class:`aio.layers.memory.MemoryBridge` instance.

        Returns:
            Mutated state (working memory updated via ``mem.encode``).
        """
        start = time.time()
        with self.obs.start_span("hitl.feedback_ingest", state.get("trace_id")):
            feedback_list = state.get("human_feedback") or []
            if feedback_list and mem is not None:
                window = state.get("context_window", [])
                for fb in feedback_list[-self.config.feedback_replay_max_corrections:]:
                    content = str(fb.get("correction", fb))
                    window.append({
                        "role": "human_feedback",
                        "content": content,
                        "turn": state.get("turn", 0),
                    })
                state["context_window"] = window
                try:
                    mem.encode(state)
                except Exception as exc:
                    logger.warning("Feedback memory ingestion failed: %s", exc)
            self.obs.record_latency("hitl.feedback_ingest", time.time() - start)
            self.obs.count_node("hitl.feedback_ingest", "success")
        return state


class EscalationPolicy:
    """Evaluates safety violations and immune anomalies for auto-escalation.

    Args:
        config: HITL configuration.
        observability: Shared observability layer.
    """

    def __init__(self, config: HitlConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    def evaluate(self, state: AIOState) -> AIOState:
        """Check thresholds and escalate if necessary.

        Sets ``escalation_reason``, ``failure_state="FAILED"``, clears ``output``,
        and sets ``error`` when thresholds are crossed.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state.
        """
        start = time.time()
        with self.obs.start_span("hitl.escalation_policy", state.get("trace_id")):
            reasons: List[str] = []
            if self.config.escalation_on_safety_violation and state.get("safety_violations"):
                reasons.append("safety_violation")
            if self.config.escalation_on_immune_alert:
                immune_status = state.get("immune_status")
                anomaly_score = state.get("anomaly_score", 0.0) or 0.0
                if immune_status == "ALERT" or anomaly_score > self.config.anomaly_threshold_for_escalation:
                    reasons.append("immune_alert")
            if reasons:
                state["escalation_reason"] = reasons
                state["failure_state"] = "FAILED"
                state["output"] = None
                state["error"] = "HITL escalation triggered: " + ", ".join(reasons)
                self.obs.count_node("hitl.escalation_policy", "escalated")
            else:
                state["escalation_reason"] = None
                self.obs.count_node("hitl.escalation_policy", "clean")
            self.obs.record_latency("hitl.escalation_policy", time.time() - start)
        return state


class FeedbackLoopEngine:
    """Periodically replays human corrections to improve planning and tool-use.

    Args:
        config: HITL configuration.
        observability: Shared observability layer.
    """

    def __init__(self, config: HitlConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._corrections: List[Dict[str, Any]] = []

    def record_correction(self, correction: Dict[str, Any]) -> None:
        """Store a human correction for future replay.

        Args:
            correction: Dict with at least ``intent`` and ``correction`` keys.
        """
        self._corrections.append(dict(correction))

    def replay(
        self,
        state: AIOState,
        planning: Optional[Any] = None,
        toolopt: Optional[Any] = None,
    ) -> AIOState:
        """Match corrections against current intent and optionally mutate plan/metrics.

        Args:
            state: Current :class:`AIOState`.
            planning: Optional :class:`aio.layers.planning.PlanningLayer`.
            toolopt: Optional :class:`aio.layers.tool_optimizer.ToolOptimizer`.

        Returns:
            Mutated state with ``feedback_suggestions`` populated.
        """
        start = time.time()
        with self.obs.start_span("hitl.feedback_loop", state.get("trace_id")):
            if not self.config.enable:
                self.obs.count_node("hitl.feedback_loop", "disabled")
                return state

            intent = (state.get("intent") or "").lower()
            suggestions: List[Dict[str, Any]] = []
            max_corr = self.config.feedback_replay_max_corrections
            for corr in self._corrections[-max_corr:]:
                corr_intent = (corr.get("intent") or "").lower()
                if not corr_intent or corr_intent == intent:
                    suggestions.append(corr)
                    if planning is not None and state.get("plan"):
                        prefix = f"[HUMAN_CORRECTION] {corr.get('correction', '')}\n"
                        state["plan"] = prefix + (state["plan"] or "")
                    if toolopt is not None and state.get("metrics") is not None:
                        state.setdefault("metrics", {})["feedback_adjusted"] = True

            state["feedback_suggestions"] = suggestions
            self.obs.record_latency("hitl.feedback_loop", time.time() - start)
            self.obs.count_node("hitl.feedback_loop", "success" if suggestions else "none")
        return state
