from __future__ import annotations

import time
from typing import Any, Dict, List

from ..config.models import ContextConfig
from .observability import ObservabilityLayer
from ..state import AIOState


class ContextManager:
    """Manages context window, BAPO attention routing, and working memory pruning."""

    def __init__(self, config: ContextConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    @staticmethod
    def approximate_token_count(text: str) -> int:
        """Rough token count: ~4 chars per token for English-like text."""
        return max(1, len(text) // 4)

    def ingest(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("context.ingest", state.get("trace_id")):
            raw = state.get("raw_input", "")
            intent = self._classify_intent(raw)
            state["intent"] = intent
            state["turn"] = state.get("turn", 0) + 1
            state["context_window"] = state.get("context_window", []) + [
                {"role": "user", "content": raw, "turn": state["turn"]}
            ]
            state["attention_map"] = {
                "memory": 0.6,
                "verify": 0.4 if intent in {"analysis", "coding"} else 0.2,
                "execute": 0.7 if intent in {"action", "tool_use"} else 0.3,
                "recover": 0.5,
            }
            self.obs.record_latency("context.ingest", time.time() - start)
            self.obs.count_node("context.ingest", "success")
        return state

    def sculpt(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("context.sculpt", state.get("trace_id")):
            window = state.get("context_window", [])
            budget = self.config.max_tokens - self.config.budget_reserve
            total = sum(self.approximate_token_count(str(msg.get("content", ""))) for msg in window)
            while total > budget and window:
                idx = self._find_prunable_index(window)
                removed = window.pop(idx)
                state.setdefault("working_memory", []).append({
                    **removed,
                    "pruned_at": time.time(),
                    "reason": "budget_overflow",
                })
                total = sum(self.approximate_token_count(str(msg.get("content", ""))) for msg in window)
            state["context_window"] = window
            state["context_budget"] = budget - total
            self.obs.set_context_budget(state["context_budget"])
            self.obs.record_latency("context.sculpt", time.time() - start)
            self.obs.count_node("context.sculpt", "success")
        return state

    def route_attention(self, state: AIOState) -> str:
        """Return next layer target based on BAPO attention map."""
        amap = dict(state.get("attention_map", {}))
        if not amap:
            return "memory"
        if state.get("failure_state") in {"DEGRADED", "RECOVERING"}:
            amap = {k: (v * 0.5 if k != "recover" else min(1.0, v + 0.3)) for k, v in amap.items()}
        target = max(amap, key=lambda k: amap[k])
        return target

    def _classify_intent(self, raw: str) -> str:
        lowered = raw.lower()
        if any(k in lowered for k in ("run", "execute", "call", "invoke", "tool")):
            return "action"
        if any(k in lowered for k in ("analyze", "review", "check", "verify", "debug")):
            return "analysis"
        if any(k in lowered for k in ("write", "code", "script", "function")):
            return "coding"
        return "general"

    def _find_prunable_index(self, window: List[Dict[str, Any]]) -> int:
        for i, msg in enumerate(window):
            if msg.get("role") != "system":
                return i
        return 0
