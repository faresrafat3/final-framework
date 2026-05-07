from __future__ import annotations

import logging
from typing import Any, Optional

from langgraph.graph import StateGraph, END

from ..config.models import AIOConfig
from ..layers.observability import ObservabilityLayer
from ..layers.context import ContextManager
from ..layers.memory import MemoryBridge
from ..layers.planning import PlanningLayer
from ..layers.curiosity import CuriosityEngine
from ..layers.verification import Verifier
from ..layers.tool_optimizer import ToolOptimizer
from ..layers.tool_gate import ToolGate
from ..layers.mcp_client import MCPClient
from ..layers.failure_recovery import FailureRecovery
from ..layers.self_evolution import SelfEvolutionLayer
from ..layers.multi_agent import MultiAgentCoordinator
from ..layers.safety_governance import SafetyGovernance
from ..layers.cognitive_immune import CognitiveImmuneSystem
from ..state import AIOState
from .nodes import (
    node_context_ingest,
    node_context_sculpt,
    node_memory_retrieve,
    node_memory_encode,
    node_memory_verify,
    node_memory_store,
    node_memory_consolidate,
    node_plan_generate,
    node_maci_select,
    node_hiplan,
    node_flare,
    node_lwm_augment,
    node_ppa_analyze,
    node_spiral_mcts,
    node_mars_reflect,
    node_vmao_decompose,
    node_curiosity_intrinsic,
    node_curiosity_seek,
    node_curiosity_serendipity,
    node_curiosity_counterfactual,
    node_curiosity_umwelt,
    node_verify_plan,
    node_debug_and_replan,
    node_gstep_evaluate,
    node_hdpo_optimize,
    node_jtpro_optimize,
    node_execute_action,
    node_analytics_record,
    node_failure_assess,
    node_retry_with_backoff,
    node_escalate,
    node_graceful_degrade,
    node_neuroshield,
    node_failure_learn,
    node_finalize_output,
    node_self_evolution_analyze,
    node_multi_agent_decompose,
    node_multi_agent_dispatch,
    node_multi_agent_aggregate,
    node_multi_agent_synthesize,
    node_safety_governance_audit,
    node_cognitive_immune_scan,
)
from .routing import (
    route_memory_confidence,
    route_verification,
    route_failure,
    route_shield,
    route_ppa,
    route_gstep,
    route_post_execution,
    route_multi_agent,
    route_safety_governance,
    route_post_finalize,
    route_self_evolution,
)


def _wrap_node(
    node_name: str,
    func: Any,
    streaming_manager: Any,
) -> Any:
    """Wrap a node callable so it emits START/END streaming events."""
    if streaming_manager is None:
        return func

    from ..streaming.manager import StreamingManager

    def wrapper(state: AIOState) -> AIOState:
        event = StreamingManager.make_event(
            layer=node_name,
            event_type="START",
            payload={},
            trace_id=state.get("trace_id"),
            turn=state.get("turn"),
            node_name=node_name,
        )
        streaming_manager.emit(event)
        try:
            result = func(state)
        except Exception as exc:
            streaming_manager.emit(
                StreamingManager.make_event(
                    layer=node_name,
                    event_type="DATA",
                    payload={"error": str(exc)},
                    trace_id=state.get("trace_id"),
                    turn=state.get("turn"),
                    node_name=node_name,
                )
            )
            raise
        streaming_manager.emit(
            StreamingManager.make_event(
                layer=node_name,
                event_type="END",
                payload={},
                trace_id=state.get("trace_id"),
                turn=state.get("turn"),
                node_name=node_name,
            )
        )
        return result

    return wrapper


def build_aio_graph(
    config: Optional[AIOConfig] = None,
    store: Optional[Any] = None,
    observability_layer: Optional[ObservabilityLayer] = None,
    streaming_manager: Optional[Any] = None,
) -> Any:
    """Build and compile the full AIO LangGraph ``StateGraph``.

    This factory wires all 13 cognitive layers as nodes and attaches the
    conditional routing edges that govern transitions between them.  The
    resulting compiled graph can be invoked with an :class:`aio.state.AIOState`
    dict.

    Args:
        config: Top-level configuration.  Defaults to ``AIOConfig()``.
        store: Optional :class:`aio.dashboard.store.AuditStore` used by
            Layer 11 (SafetyGovernance) to persist audit decisions.
        observability_layer: Optional :class:`aio.layers.observability.ObservabilityLayer`.
            When omitted a default instance is created from ``config.observability``.
        streaming_manager: Optional :class:`aio.streaming.StreamingManager`.
            When provided, every node wrapper emits ``START``/``END`` events
            fire-and-forget during graph execution.

    Returns:
        A compiled LangGraph object (``CompiledStateGraph``) exposing
        ``invoke()``, ``stream()``, etc.

    Raises:
        ImportError: If ``langgraph`` is not installed.

    Example::

        from aio import AIOConfig, build_aio_graph, make_initial_state
        graph = build_aio_graph(AIOConfig())
        result = graph.invoke(make_initial_state("echo hello"))
    """
    cfg = config or AIOConfig()
    obs = observability_layer or ObservabilityLayer(cfg.observability)
    ctx_mgr = ContextManager(cfg.context, obs)
    mem = MemoryBridge(cfg.memory, obs)
    planning = PlanningLayer(cfg.planning, obs)
    curiosity = CuriosityEngine(cfg.curiosity, obs)
    verifier = Verifier(cfg.verifier, obs)
    toolopt = ToolOptimizer(cfg.tool_optimizer, obs)
    mcp_client: Optional[Any] = None
    if cfg.mcp.enable:
        try:
            mcp_client = MCPClient(cfg.mcp, obs)
        except Exception as exc:
            obs.log(logging.WARNING, f"MCP client instantiation failed: {exc}")
    toolgate = ToolGate(cfg.toolgate, obs, mcp_client=mcp_client)
    recovery = FailureRecovery(cfg.failure_recovery, obs)

    graph = StateGraph(AIOState)

    # Helper to optionally wrap with streaming emission
    def _add(name: str, fn: Any) -> None:
        graph.add_node(name, _wrap_node(name, fn, streaming_manager))

    # Layer 1
    _add("context_ingest", lambda s: node_context_ingest(s, ctx_mgr))
    _add("context_sculpt", lambda s: node_context_sculpt(s, ctx_mgr))

    # Layer 2
    _add("memory_retrieve", lambda s: node_memory_retrieve(s, mem))
    _add("memory_encode", lambda s: node_memory_encode(s, mem))
    _add("memory_verify", lambda s: node_memory_verify(s, mem))
    _add("memory_store", lambda s: node_memory_store(s, mem))
    _add("memory_consolidate", lambda s: node_memory_consolidate(s, mem))

    # Layer 4
    _add("curiosity_intrinsic", lambda s: node_curiosity_intrinsic(s, curiosity))
    _add("curiosity_seek", lambda s: node_curiosity_seek(s, curiosity))
    _add("curiosity_serendipity", lambda s: node_curiosity_serendipity(s, curiosity))
    _add("curiosity_counterfactual", lambda s: node_curiosity_counterfactual(s, curiosity))
    _add("curiosity_umwelt", lambda s: node_curiosity_umwelt(s, curiosity))

    # Planning stub (generates base plan)
    _add("plan_generate", lambda s: node_plan_generate(s, planning))

    # Layer 3
    _add("maci_select", lambda s: node_maci_select(s, planning))
    _add("hiplan", lambda s: node_hiplan(s, planning))
    _add("flare", lambda s: node_flare(s, planning))
    _add("lwm_augment", lambda s: node_lwm_augment(s, planning))
    _add("ppa_analyze", lambda s: node_ppa_analyze(s, planning))
    _add("spiral_mcts", lambda s: node_spiral_mcts(s, planning))
    _add("mars_reflect", lambda s: node_mars_reflect(s, planning))
    _add("vmao_decompose", lambda s: node_vmao_decompose(s, planning))

    # Layer 5
    _add("verify_plan", lambda s: node_verify_plan(s, verifier))
    _add("debug_and_replan", lambda s: node_debug_and_replan(s, verifier))

    # Layer 6
    _add("gstep_evaluate", lambda s: node_gstep_evaluate(s, toolopt))
    _add("hdpo_optimize", lambda s: node_hdpo_optimize(s, toolopt))
    _add("jtpro_optimize", lambda s: node_jtpro_optimize(s, toolopt))
    _add("execute_action", lambda s: node_execute_action(s, toolgate))
    _add("analytics_record", lambda s: node_analytics_record(s, toolopt))

    # Layer 8
    _add("failure_assess", lambda s: node_failure_assess(s, recovery))
    _add("retry_with_backoff", lambda s: node_retry_with_backoff(s, recovery))
    _add("escalate", lambda s: node_escalate(s, recovery))
    _add("graceful_degrade", lambda s: node_graceful_degrade(s, recovery))
    _add("neuroshield", lambda s: node_neuroshield(s, recovery))
    _add("failure_learn", lambda s: node_failure_learn(s, recovery))

    # Layer 9-12 nodes (added unconditionally; routing decides if they run)
    self_evol = SelfEvolutionLayer(cfg.self_evolution, obs)
    multi_agent = MultiAgentCoordinator(cfg.multi_agent, obs)
    governance = SafetyGovernance(cfg.safety_governance, obs, store=store)
    immune = CognitiveImmuneSystem(cfg.cognitive_immune, obs)

    _add("self_evolution_analyze", lambda s: node_self_evolution_analyze(s, self_evol))
    _add("multi_agent_decompose", lambda s: node_multi_agent_decompose(s, multi_agent))
    _add("multi_agent_dispatch", lambda s: node_multi_agent_dispatch(s, multi_agent))
    _add("multi_agent_aggregate", lambda s: node_multi_agent_aggregate(s, multi_agent))
    _add("multi_agent_synthesize", lambda s: node_multi_agent_synthesize(s, multi_agent))
    _add("safety_governance_audit", lambda s: node_safety_governance_audit(s, governance))
    _add("cognitive_immune_scan", lambda s: node_cognitive_immune_scan(s, immune))

    # Finalize
    _add("finalize_output", node_finalize_output)

    # Entry point
    graph.set_entry_point("context_ingest")

    # Layer 1 -> NeuroShield
    graph.add_edge("context_ingest", "context_sculpt")
    graph.add_edge("context_sculpt", "neuroshield")
    graph.add_conditional_edges("neuroshield", route_shield)

    # Escalate from neuroshield -> failure_learn -> finalize
    graph.add_edge("escalate", "failure_learn")

    # Memory branch
    graph.add_conditional_edges("memory_retrieve", route_memory_confidence)
    graph.add_edge("memory_encode", "memory_verify")
    graph.add_edge("memory_verify", "memory_store")
    graph.add_edge("memory_store", "memory_consolidate")
    graph.add_edge("memory_consolidate", "curiosity_intrinsic")

    # Curiosity pipeline
    graph.add_edge("curiosity_intrinsic", "curiosity_seek")
    graph.add_edge("curiosity_seek", "curiosity_serendipity")
    graph.add_edge("curiosity_serendipity", "curiosity_counterfactual")
    graph.add_edge("curiosity_counterfactual", "curiosity_umwelt")
    graph.add_edge("curiosity_umwelt", "plan_generate")

    # Planning pipeline
    graph.add_edge("plan_generate", "maci_select")
    graph.add_conditional_edges("maci_select", lambda s: route_multi_agent(s, cfg))
    graph.add_edge("hiplan", "flare")
    graph.add_edge("multi_agent_decompose", "multi_agent_dispatch")
    graph.add_edge("multi_agent_dispatch", "multi_agent_aggregate")
    graph.add_edge("multi_agent_aggregate", "multi_agent_synthesize")
    graph.add_edge("multi_agent_synthesize", "flare")
    graph.add_edge("flare", "lwm_augment")
    graph.add_edge("lwm_augment", "ppa_analyze")
    graph.add_conditional_edges("ppa_analyze", route_ppa)
    graph.add_edge("spiral_mcts", "mars_reflect")
    graph.add_edge("mars_reflect", "vmao_decompose")
    graph.add_conditional_edges("vmao_decompose", lambda s: route_safety_governance(s, cfg))
    graph.add_edge("safety_governance_audit", "verify_plan")

    # Verification branch
    graph.add_conditional_edges("verify_plan", route_verification)
    graph.add_edge("debug_and_replan", "verify_plan")

    # Tool-use optimization -> execution -> analytics
    graph.add_conditional_edges("gstep_evaluate", route_gstep)
    graph.add_edge("hdpo_optimize", "jtpro_optimize")
    graph.add_edge("jtpro_optimize", "execute_action")
    graph.add_edge("execute_action", "analytics_record")
    graph.add_conditional_edges("analytics_record", route_post_execution)

    # Failure recovery branch
    graph.add_conditional_edges("failure_assess", route_failure)
    graph.add_edge("retry_with_backoff", "verify_plan")
    graph.add_edge("escalate", "failure_learn")
    graph.add_edge("graceful_degrade", "failure_learn")
    graph.add_edge("failure_learn", "finalize_output")

    # Post-finalize reflection pipeline
    graph.add_conditional_edges("finalize_output", lambda s: route_post_finalize(s, cfg))
    graph.add_edge("self_evolution_analyze", "cognitive_immune_scan")
    graph.add_conditional_edges("cognitive_immune_scan", lambda s: route_self_evolution(s, cfg))

    return graph.compile()
