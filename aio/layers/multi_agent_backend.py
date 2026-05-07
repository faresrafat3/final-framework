from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from langgraph.graph import StateGraph, END

from ..config.models import MultiAgentConfig
from .observability import ObservabilityLayer
from ..state import AIOState


class SimulatedMultiAgentBackend:
    """Fallback simulated backend that mimics multi-agent dispatch without LLMs.

    Args:
        config: Layer 10 configuration.
        observability: Shared observability layer.
        registry: Optional agent-role registry override.
    """

    def __init__(
        self,
        config: MultiAgentConfig,
        observability: ObservabilityLayer,
        registry: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.config = config
        self.obs = observability
        self._registry = registry or {
            "coder": {"role": "Implementation", "strengths": ["code", "debug", "refactor"]},
            "analyst": {"role": "Analysis", "strengths": ["data", "patterns", "summary"]},
            "planner": {"role": "Strategy", "strengths": ["decompose", "dependencies", "schedule"]},
            "safety_officer": {"role": "Safety", "strengths": ["risk", "compliance", "boundaries"]},
        }

    def dispatch(self, state: AIOState) -> AIOState:
        """Simulate execution of every subtask in the coordination plan.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``agent_outputs``.
        """
        start = time.time()
        with self.obs.start_span("multi_agent.dispatch.simulated", state.get("trace_id")):
            plan = state.get("coordination_plan", {})
            subtasks = plan.get("subtasks", [])
            outputs: Dict[str, Any] = {}
            for st in subtasks:
                agent = st.get("agent", "unknown")
                confidence = round(0.7 + (0.25 if agent in self._registry else 0.0), 4)
                outputs[st["id"]] = {
                    "agent": agent,
                    "confidence": confidence,
                    "result": f"Simulated output from {agent} for {st.get('description', '')}",
                }
            state["agent_outputs"] = outputs
            self.obs.record_latency("multi_agent.dispatch.simulated", time.time() - start)
            self.obs.count_node("multi_agent.dispatch.simulated", "success")
        return state


class LangGraphMultiAgentBackend:
    """Real multi-agent dispatch using LangGraph native supervisor/hierarchical sub-graphs.

    Each registered agent is modelled as a sub-graph node. A lightweight supervisor
    routes subtasks to the appropriate agent sub-graph, collects results, and writes
    them back into ``agent_outputs``. If anything goes wrong it falls back to the
    simulated backend automatically so callers never crash.

    Args:
        config: Layer 10 configuration.
        observability: Shared observability layer.
        registry: Optional agent-role registry override.
        agent_callables: Optional dict of callables for real LLM-backed agents.
    """

    def __init__(
        self,
        config: MultiAgentConfig,
        observability: ObservabilityLayer,
        registry: Optional[Dict[str, Dict[str, Any]]] = None,
        agent_callables: Optional[Dict[str, Callable[[AIOState], AIOState]]] = None,
    ) -> None:
        self.config = config
        self.obs = observability
        self._registry = registry or {
            "coder": {"role": "Implementation", "strengths": ["code", "debug", "refactor"]},
            "analyst": {"role": "Analysis", "strengths": ["data", "patterns", "summary"]},
            "planner": {"role": "Strategy", "strengths": ["decompose", "dependencies", "schedule"]},
            "safety_officer": {"role": "Safety", "strengths": ["risk", "compliance", "boundaries"]},
        }
        # Agent callables can be injected for real LLM-backed behaviour.
        # When none are provided we build simple passthrough nodes that
        # annotate the state the same way the simulated backend does.
        self._agent_callables = agent_callables or {}
        self._fallback = SimulatedMultiAgentBackend(config, observability, self._registry)
        self._subgraph: Any = self._build_supervisor_subgraph()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def dispatch(self, state: AIOState) -> AIOState:
        """Invoke the compiled supervisor sub-graph and copy results back.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``agent_outputs`` and ``consensus_score``.
        """
        start = time.time()
        with self.obs.start_span("multi_agent.dispatch.langgraph", state.get("trace_id")):
            try:
                state = self._run_subgraph(state)
            except Exception as exc:
                self.obs.count_node("multi_agent.dispatch.langgraph", "error")
                state = self._fallback.dispatch(state)
                state["metrics"] = state.get("metrics", {})
                state["metrics"]["multi_agent_fallback_reason"] = str(exc)
            self.obs.record_latency("multi_agent.dispatch.langgraph", time.time() - start)
        return state

    # ------------------------------------------------------------------
    # Sub-graph construction (supervisor pattern)
    # ------------------------------------------------------------------

    def _build_supervisor_subgraph(self) -> Any:
        """Build and compile a LangGraph supervisor sub-graph."""
        graph = StateGraph(AIOState)

        # Supervisor node: prepares the execution queue.
        graph.add_node("supervisor", self._node_supervisor)

        # Dispatcher node: runs the next agent in the queue and pops it.
        graph.add_node("dispatch_one", self._node_dispatch_one)

        # Aggregate node: computes consensus after all agents ran.
        graph.add_node("aggregate", self._node_aggregate)

        # Entry point.
        graph.set_entry_point("supervisor")

        # After supervisor go straight to dispatch_one.
        graph.add_edge("supervisor", "dispatch_one")

        # After dispatch_one either loop back (more agents) or finish.
        graph.add_conditional_edges("dispatch_one", self._route_after_dispatch)

        graph.add_edge("aggregate", END)

        return graph.compile()

    def _node_supervisor(self, state: AIOState) -> AIOState:
        plan = state.get("coordination_plan", {})
        subtasks = plan.get("subtasks", [])
        # Determine which agents are needed.
        needed = {st.get("agent", "unknown") for st in subtasks}
        # Store the execution order inside the state so the router can read it.
        state["_ma_needed_agents"] = sorted(needed & set(self._registry.keys()))
        state["_ma_subtasks"] = subtasks
        # Initialise partial outputs bucket.
        if not state.get("agent_outputs"):
            state["agent_outputs"] = {}
        return state

    def _node_dispatch_one(self, state: AIOState) -> AIOState:
        """Run the next agent in ``_ma_needed_agents`` and pop it from the queue."""
        needed = state.get("_ma_needed_agents", [])
        if not needed:
            return state
        # Copy the list so we mutate our own version.
        queue = list(needed)
        agent_name = queue.pop(0)
        state["_ma_needed_agents"] = queue

        subtasks = state.get("_ma_subtasks", [])
        outputs = dict(state.get("agent_outputs", {}))
        for st in subtasks:
            if st.get("agent") != agent_name:
                continue
            fn = self._agent_callables.get(agent_name)
            if fn is not None:
                sub_state = fn(state)
                outputs.update(sub_state.get("agent_outputs", {}))
            else:
                confidence = round(0.7 + (0.25 if agent_name in self._registry else 0.0), 4)
                outputs[st["id"]] = {
                    "agent": agent_name,
                    "confidence": confidence,
                    "result": f"LangGraph sub-agent output from {agent_name} for {st.get('description', '')}",
                }
        state["agent_outputs"] = outputs
        return state

    def _route_after_dispatch(self, state: AIOState) -> str:
        needed = state.get("_ma_needed_agents", [])
        if not needed:
            return "aggregate"
        return "dispatch_one"

    def _node_aggregate(self, state: AIOState) -> AIOState:
        outputs = state.get("agent_outputs", {})
        if not outputs:
            consensus = 0.0
        else:
            confidences = [o.get("confidence", 0.0) for o in outputs.values()]
            avg_conf = sum(confidences) / len(confidences)
            variance = sum((c - avg_conf) ** 2 for c in confidences) / len(confidences)
            consensus = round(max(0.0, avg_conf - variance), 4)
        state["consensus_score"] = consensus
        return state

    def _run_subgraph(self, state: AIOState) -> AIOState:
        """Invoke the compiled sub-graph and copy outputs back into *state*."""
        # The subgraph is compiled so it expects a dict-like state.
        result = self._subgraph.invoke(state)
        # Copy the outputs back into the original state to keep types consistent.
        state["agent_outputs"] = result.get("agent_outputs", {})
        state["consensus_score"] = result.get("consensus_score", 0.0)
        return state
