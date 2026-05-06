from __future__ import annotations

import time
from typing import Any, Dict, Optional

from ..config.models import MultiAgentConfig
from .observability import ObservabilityLayer
from ..state import AIOState
from .multi_agent_backend import SimulatedMultiAgentBackend, LangGraphMultiAgentBackend


class MultiAgentCoordinator:
    """Decomposes complex tasks across registered agents and synthesizes consensus.

    ``dispatch`` is backed by a pluggable backend.  When
    ``config.use_langgraph_backend`` is *True* the native LangGraph
    supervisor/hierarchical backend is used; otherwise the legacy simulated
    loop is used for backward compatibility.
    """

    def __init__(self, config: MultiAgentConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._registry: Dict[str, Dict[str, Any]] = {
            "coder": {"role": "Implementation", "strengths": ["code", "debug", "refactor"]},
            "analyst": {"role": "Analysis", "strengths": ["data", "patterns", "summary"]},
            "planner": {"role": "Strategy", "strengths": ["decompose", "dependencies", "schedule"]},
            "safety_officer": {"role": "Safety", "strengths": ["risk", "compliance", "boundaries"]},
        }
        self._simulated_backend = SimulatedMultiAgentBackend(config, observability, self._registry)
        self._langgraph_backend: Optional[LangGraphMultiAgentBackend] = None
        if getattr(config, "use_langgraph_backend", False):
            self._langgraph_backend = LangGraphMultiAgentBackend(config, observability, self._registry)

    def decompose(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("multi_agent.decompose", state.get("trace_id")):
            intent = state.get("intent", "general")
            plan = state.get("plan", "")
            subtasks = []
            if intent in {"coding", "analysis"}:
                subtasks.append({"id": "st-1", "agent": "planner", "description": "Decompose requirements"})
                subtasks.append({"id": "st-2", "agent": "coder" if intent == "coding" else "analyst", "description": "Execute core task"})
                subtasks.append({"id": "st-3", "agent": "safety_officer", "description": "Verify compliance"})
            else:
                subtasks.append({"id": "st-1", "agent": "planner", "description": "Plan task"})
                subtasks.append({"id": "st-2", "agent": "analyst", "description": "Analyze context"})
            state["coordination_plan"] = {"subtasks": subtasks, "intent": intent, "plan": plan}
            self.obs.record_latency("multi_agent.decompose", time.time() - start)
            self.obs.count_node("multi_agent.decompose", "success")
        return state

    def dispatch(self, state: AIOState) -> AIOState:
        if self._langgraph_backend is not None:
            return self._langgraph_backend.dispatch(state)
        return self._simulated_backend.dispatch(state)

    def aggregate(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("multi_agent.aggregate", state.get("trace_id")):
            outputs = state.get("agent_outputs", {})
            if not outputs:
                consensus = 0.0
            else:
                confidences = [o.get("confidence", 0.0) for o in outputs.values()]
                avg_conf = sum(confidences) / len(confidences)
                variance = sum((c - avg_conf) ** 2 for c in confidences) / len(confidences)
                consensus = round(max(0.0, avg_conf - variance), 4)
            state["consensus_score"] = consensus
            self.obs.record_latency("multi_agent.aggregate", time.time() - start)
            self.obs.count_node("multi_agent.aggregate", "success")
        return state

    def synthesize(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("multi_agent.synthesize", state.get("trace_id")):
            outputs = state.get("agent_outputs", {})
            parts = [o.get("result", "") for o in outputs.values()]
            unified = " | ".join(parts) if parts else "No agent outputs"
            state["plan"] = unified
            self.obs.record_latency("multi_agent.synthesize", time.time() - start)
            self.obs.count_node("multi_agent.synthesize", "success")
        return state
