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


def build_aio_graph(config: Optional[AIOConfig] = None, store: Optional[Any] = None) -> Any:
    """Build and compile the Priority 2 AIO StateGraph."""
    cfg = config or AIOConfig()
    obs = ObservabilityLayer(cfg.observability)
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

    # Layer 1
    graph.add_node("context_ingest", lambda s: node_context_ingest(s, ctx_mgr))
    graph.add_node("context_sculpt", lambda s: node_context_sculpt(s, ctx_mgr))

    # Layer 2
    graph.add_node("memory_retrieve", lambda s: node_memory_retrieve(s, mem))
    graph.add_node("memory_encode", lambda s: node_memory_encode(s, mem))
    graph.add_node("memory_verify", lambda s: node_memory_verify(s, mem))
    graph.add_node("memory_store", lambda s: node_memory_store(s, mem))
    graph.add_node("memory_consolidate", lambda s: node_memory_consolidate(s, mem))

    # Layer 4
    graph.add_node("curiosity_intrinsic", lambda s: node_curiosity_intrinsic(s, curiosity))
    graph.add_node("curiosity_seek", lambda s: node_curiosity_seek(s, curiosity))
    graph.add_node("curiosity_serendipity", lambda s: node_curiosity_serendipity(s, curiosity))
    graph.add_node("curiosity_counterfactual", lambda s: node_curiosity_counterfactual(s, curiosity))
    graph.add_node("curiosity_umwelt", lambda s: node_curiosity_umwelt(s, curiosity))

    # Planning stub (generates base plan)
    graph.add_node("plan_generate", lambda s: node_plan_generate(s, planning))

    # Layer 3
    graph.add_node("maci_select", lambda s: node_maci_select(s, planning))
    graph.add_node("hiplan", lambda s: node_hiplan(s, planning))
    graph.add_node("flare", lambda s: node_flare(s, planning))
    graph.add_node("lwm_augment", lambda s: node_lwm_augment(s, planning))
    graph.add_node("ppa_analyze", lambda s: node_ppa_analyze(s, planning))
    graph.add_node("spiral_mcts", lambda s: node_spiral_mcts(s, planning))
    graph.add_node("mars_reflect", lambda s: node_mars_reflect(s, planning))
    graph.add_node("vmao_decompose", lambda s: node_vmao_decompose(s, planning))

    # Layer 5
    graph.add_node("verify_plan", lambda s: node_verify_plan(s, verifier))
    graph.add_node("debug_and_replan", lambda s: node_debug_and_replan(s, verifier))

    # Layer 6
    graph.add_node("gstep_evaluate", lambda s: node_gstep_evaluate(s, toolopt))
    graph.add_node("hdpo_optimize", lambda s: node_hdpo_optimize(s, toolopt))
    graph.add_node("jtpro_optimize", lambda s: node_jtpro_optimize(s, toolopt))
    graph.add_node("execute_action", lambda s: node_execute_action(s, toolgate))
    graph.add_node("analytics_record", lambda s: node_analytics_record(s, toolopt))

    # Layer 8
    graph.add_node("failure_assess", lambda s: node_failure_assess(s, recovery))
    graph.add_node("retry_with_backoff", lambda s: node_retry_with_backoff(s, recovery))
    graph.add_node("escalate", lambda s: node_escalate(s, recovery))
    graph.add_node("graceful_degrade", lambda s: node_graceful_degrade(s, recovery))
    graph.add_node("neuroshield", lambda s: node_neuroshield(s, recovery))
    graph.add_node("failure_learn", lambda s: node_failure_learn(s, recovery))

    # Layer 9-12 nodes (added unconditionally; routing decides if they run)
    self_evol = SelfEvolutionLayer(cfg.self_evolution, obs)
    multi_agent = MultiAgentCoordinator(cfg.multi_agent, obs)
    governance = SafetyGovernance(cfg.safety_governance, obs, store=store)
    immune = CognitiveImmuneSystem(cfg.cognitive_immune, obs)

    graph.add_node("self_evolution_analyze", lambda s: node_self_evolution_analyze(s, self_evol))
    graph.add_node("multi_agent_decompose", lambda s: node_multi_agent_decompose(s, multi_agent))
    graph.add_node("multi_agent_dispatch", lambda s: node_multi_agent_dispatch(s, multi_agent))
    graph.add_node("multi_agent_aggregate", lambda s: node_multi_agent_aggregate(s, multi_agent))
    graph.add_node("multi_agent_synthesize", lambda s: node_multi_agent_synthesize(s, multi_agent))
    graph.add_node("safety_governance_audit", lambda s: node_safety_governance_audit(s, governance))
    graph.add_node("cognitive_immune_scan", lambda s: node_cognitive_immune_scan(s, immune))

    # Finalize
    graph.add_node("finalize_output", node_finalize_output)

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
