from __future__ import annotations

from typing import Any, Optional

from ..layers.context import ContextManager
from ..layers.memory import MemoryBridge
from ..layers.planning import PlanningLayer
from ..layers.curiosity import CuriosityEngine
from ..layers.verification import Verifier
from ..layers.tool_optimizer import ToolOptimizer
from ..layers.tool_gate import ToolGate
from ..layers.mcp_client import MCPClient, node_mcp_discover
from ..layers.failure_recovery import FailureRecovery
from ..layers.self_evolution import SelfEvolutionLayer
from ..layers.multi_agent import MultiAgentCoordinator
from ..layers.safety_governance import SafetyGovernance
from ..layers.cognitive_immune import CognitiveImmuneSystem
from ..layers.neuro_symbolic import NeuroSymbolicMandate
from ..state import AIOState


# Layer metadata mapping node_name -> (layer_name, layer_number)
_LAYER_MAP: dict[str, tuple[str, int]] = {
    "context_ingest": ("Layer 1 — Context", 1),
    "context_sculpt": ("Layer 1 — Context", 1),
    "memory_retrieve": ("Layer 2 — Memory", 2),
    "memory_encode": ("Layer 2 — Memory", 2),
    "memory_verify": ("Layer 2 — Memory", 2),
    "memory_store": ("Layer 2 — Memory", 2),
    "memory_consolidate": ("Layer 2 — Memory", 2),
    "plan_generate": ("Layer 3 — Planning", 3),
    "maci_select": ("Layer 3 — Planning", 3),
    "hiplan": ("Layer 3 — Planning", 3),
    "flare": ("Layer 3 — Planning", 3),
    "lwm_augment": ("Layer 3 — Planning", 3),
    "ppa_analyze": ("Layer 3 — Planning", 3),
    "spiral_mcts": ("Layer 3 — Planning", 3),
    "mars_reflect": ("Layer 3 — Planning", 3),
    "vmao_decompose": ("Layer 3 — Planning", 3),
    "curiosity_intrinsic": ("Layer 4 — Curiosity", 4),
    "curiosity_seek": ("Layer 4 — Curiosity", 4),
    "curiosity_serendipity": ("Layer 4 — Curiosity", 4),
    "curiosity_counterfactual": ("Layer 4 — Curiosity", 4),
    "curiosity_umwelt": ("Layer 4 — Curiosity", 4),
    "verify_plan": ("Layer 5 — Verification", 5),
    "debug_and_replan": ("Layer 5 — Verification", 5),
    "gstep_evaluate": ("Layer 6 — Tool Optimizer", 6),
    "hdpo_optimize": ("Layer 6 — Tool Optimizer", 6),
    "jtpro_optimize": ("Layer 6 — Tool Optimizer", 6),
    "analytics_record": ("Layer 6 — Tool Optimizer", 6),
    "execute_action": ("Layer 7 — Execution", 7),
    "failure_assess": ("Layer 8 — Failure Recovery", 8),
    "retry_with_backoff": ("Layer 8 — Failure Recovery", 8),
    "escalate": ("Layer 8 — Failure Recovery", 8),
    "graceful_degrade": ("Layer 8 — Failure Recovery", 8),
    "neuroshield": ("Layer 8 — Failure Recovery", 8),
    "failure_learn": ("Layer 8 — Failure Recovery", 8),
    "finalize_output": ("Layer 8 — Failure Recovery", 8),
    "self_evolution_analyze": ("Layer 9 — Self-Evolution", 9),
    "multi_agent_decompose": ("Layer 10 — Multi-Agent", 10),
    "multi_agent_dispatch": ("Layer 10 — Multi-Agent", 10),
    "multi_agent_aggregate": ("Layer 10 — Multi-Agent", 10),
    "multi_agent_synthesize": ("Layer 10 — Multi-Agent", 10),
    "safety_governance_audit": ("Layer 11 — Safety & Governance", 11),
    "cognitive_immune_scan": ("Layer 12 — Cognitive Immune", 12),
    "neuro_symbolic_parse": ("Neuro-Symbolic Mandate", 13),
    "neuro_symbolic_infer": ("Neuro-Symbolic Mandate", 13),
    "neuro_symbolic_ground": ("Neuro-Symbolic Mandate", 13),
    "neuro_symbolic_verify": ("Neuro-Symbolic Mandate", 13),
    "neuro_symbolic_synthesize": ("Neuro-Symbolic Mandate", 13),
}


def _emit(
    state: AIOState,
    node_name: str,
    event_type: str,
    streaming_manager: Any,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    if streaming_manager is None:
        return
    layer_name, _ = _LAYER_MAP.get(node_name, (node_name, 0))
    event = streaming_manager.make_event(
        layer=layer_name,
        event_type=event_type,
        payload=payload or {},
        trace_id=state.get("trace_id"),
        turn=state.get("turn"),
        node_name=node_name,
    )
    streaming_manager.emit(event)


def _wrap_node(
    func: Any,
    node_name: str,
    streaming_manager: Any,
) -> Any:
    def wrapper(state: AIOState, *args: Any, **kwargs: Any) -> AIOState:
        _emit(state, node_name, "START", streaming_manager)
        try:
            result = func(state, *args, **kwargs)
        except Exception as exc:
            _emit(
                state,
                node_name,
                "DATA",
                streaming_manager,
                payload={"error": str(exc)},
            )
            raise
        _emit(state, node_name, "END", streaming_manager)
        return result
    return wrapper


# Layer 1 nodes

def node_context_ingest(state: AIOState, ctx_mgr: ContextManager, streaming_manager: Any = None) -> AIOState:
    return ctx_mgr.ingest(state)


def node_context_sculpt(state: AIOState, ctx_mgr: ContextManager, streaming_manager: Any = None) -> AIOState:
    return ctx_mgr.sculpt(state)


# Layer 2 nodes

def node_memory_retrieve(state: AIOState, mem: MemoryBridge, streaming_manager: Any = None) -> AIOState:
    return mem.retrieve(state)


def node_memory_encode(state: AIOState, mem: MemoryBridge, streaming_manager: Any = None) -> AIOState:
    return mem.encode(state)


def node_memory_verify(state: AIOState, mem: MemoryBridge, streaming_manager: Any = None) -> AIOState:
    return mem.verify(state)


def node_memory_store(state: AIOState, mem: MemoryBridge, streaming_manager: Any = None) -> AIOState:
    return mem.store(state)


def node_memory_consolidate(state: AIOState, mem: MemoryBridge, streaming_manager: Any = None) -> AIOState:
    return mem.consolidate(state)


# Planning stub

def node_plan_generate(state: AIOState, planning: PlanningLayer, streaming_manager: Any = None) -> AIOState:
    return planning.generate_plan(state)


# Layer 3 nodes

def node_maci_select(state: AIOState, planning: PlanningLayer, streaming_manager: Any = None) -> AIOState:
    return planning.run_maci(state)


def node_hiplan(state: AIOState, planning: PlanningLayer, streaming_manager: Any = None) -> AIOState:
    return planning.run_hiplan(state)


def node_flare(state: AIOState, planning: PlanningLayer, streaming_manager: Any = None) -> AIOState:
    return planning.run_flare(state)


def node_lwm_augment(state: AIOState, planning: PlanningLayer, streaming_manager: Any = None) -> AIOState:
    return planning.run_lwm(state)


def node_ppa_analyze(state: AIOState, planning: PlanningLayer, streaming_manager: Any = None) -> AIOState:
    return planning.run_ppa(state)


def node_spiral_mcts(state: AIOState, planning: PlanningLayer, streaming_manager: Any = None) -> AIOState:
    return planning.run_spiral(state)


def node_mars_reflect(state: AIOState, planning: PlanningLayer, streaming_manager: Any = None) -> AIOState:
    return planning.run_mars(state)


def node_vmao_decompose(state: AIOState, planning: PlanningLayer, streaming_manager: Any = None) -> AIOState:
    return planning.run_vmao_decompose(state)


# Layer 4 nodes

def node_curiosity_intrinsic(state: AIOState, curiosity: CuriosityEngine, streaming_manager: Any = None) -> AIOState:
    return curiosity.intrinsic_reward(state)


def node_curiosity_seek(state: AIOState, curiosity: CuriosityEngine, streaming_manager: Any = None) -> AIOState:
    return curiosity.active_seek(state)


def node_curiosity_serendipity(state: AIOState, curiosity: CuriosityEngine, streaming_manager: Any = None) -> AIOState:
    return curiosity.serendipity(state)


def node_curiosity_counterfactual(state: AIOState, curiosity: CuriosityEngine, streaming_manager: Any = None) -> AIOState:
    return curiosity.counterfactual(state)


def node_curiosity_umwelt(state: AIOState, curiosity: CuriosityEngine, streaming_manager: Any = None) -> AIOState:
    return curiosity.umwelt_constraints(state)


# Layer 5 nodes

def node_verify_plan(state: AIOState, verifier: Verifier, streaming_manager: Any = None) -> AIOState:
    state = verifier.critique(state)
    state = verifier.judge(state)
    state = verifier.score(state)
    state = verifier.debug(state)
    return state


def node_debug_and_replan(state: AIOState, verifier: Verifier, streaming_manager: Any = None) -> AIOState:
    result = state.get("verification_result", {})
    hypotheses = result.get("debug_hypotheses", [])
    existing = state.get("plan") or ""
    if hypotheses:
        replan_text = "[REPLAN] " + "; ".join(hypotheses)
    else:
        replan_text = "[REPLAN] no plan"
    enriched = replan_text + " Step 1: analyze. Step 2: execute action. Step 3: finalize."
    state["plan"] = enriched
    state["verification_result"] = {}
    return state


# Layer 6 nodes

def node_gstep_evaluate(state: AIOState, toolopt: ToolOptimizer, streaming_manager: Any = None) -> AIOState:
    return toolopt.gstep_evaluate(state)


def node_hdpo_optimize(state: AIOState, toolopt: ToolOptimizer, streaming_manager: Any = None) -> AIOState:
    return toolopt.hdpo_optimize(state)


def node_jtpro_optimize(state: AIOState, toolopt: ToolOptimizer, streaming_manager: Any = None) -> AIOState:
    return toolopt.jtpro_optimize(state)


def node_sandbox_execute(state: AIOState, toolopt: ToolOptimizer, toolgate: ToolGate, streaming_manager: Any = None) -> AIOState:
    return toolopt.sandbox_execute(state, toolgate)


def node_analytics_record(state: AIOState, toolopt: ToolOptimizer, streaming_manager: Any = None) -> AIOState:
    return toolopt.analytics_record(state)


# Layer 7 node

def node_execute_action(state: AIOState, toolgate: ToolGate, streaming_manager: Any = None) -> AIOState:
    return toolgate.execute(state)


# Layer 8 nodes

def node_failure_assess(state: AIOState, recovery: FailureRecovery, streaming_manager: Any = None) -> AIOState:
    return recovery.assess(state)


def node_retry_with_backoff(state: AIOState, recovery: FailureRecovery, streaming_manager: Any = None) -> AIOState:
    return recovery.retry(state)


def node_escalate(state: AIOState, recovery: FailureRecovery, streaming_manager: Any = None) -> AIOState:
    return recovery.escalate(state)


def node_graceful_degrade(state: AIOState, recovery: FailureRecovery, streaming_manager: Any = None) -> AIOState:
    return recovery.degrade(state)


def node_neuroshield(state: AIOState, recovery: FailureRecovery, streaming_manager: Any = None) -> AIOState:
    return recovery.shield(state)


def node_failure_learn(state: AIOState, recovery: FailureRecovery, streaming_manager: Any = None) -> AIOState:
    return recovery.learn(state)


def node_finalize_output(state: AIOState, streaming_manager: Any = None) -> AIOState:
    if state.get("error"):
        state["output"] = f"[ERROR] {state['error']}"
    elif state.get("execution_result"):
        exec_res = state["execution_result"]
        if exec_res.get("success"):
            state["output"] = exec_res.get("stdout", "") or "[OK]"
        else:
            state["output"] = exec_res.get("stderr", "") or "[NO OUTPUT]"
    else:
        state["output"] = state.get("output") or "[NO OUTPUT]"
    return state


# Layer 9 nodes

def node_self_evolution_analyze(state: AIOState, layer: SelfEvolutionLayer, streaming_manager: Any = None) -> AIOState:
    state = layer.analyze(state)
    state = layer.generate_report(state)
    state = layer.suggest_improvements(state)
    state = layer.apply_deltas(state)
    return state


# Layer 10 nodes

def node_multi_agent_decompose(state: AIOState, layer: MultiAgentCoordinator, streaming_manager: Any = None) -> AIOState:
    return layer.decompose(state)


def node_multi_agent_dispatch(state: AIOState, layer: MultiAgentCoordinator, streaming_manager: Any = None) -> AIOState:
    return layer.dispatch(state)


def node_multi_agent_aggregate(state: AIOState, layer: MultiAgentCoordinator, streaming_manager: Any = None) -> AIOState:
    return layer.aggregate(state)


def node_multi_agent_synthesize(state: AIOState, layer: MultiAgentCoordinator, streaming_manager: Any = None) -> AIOState:
    return layer.synthesize(state)


# Layer 11 nodes

def node_safety_governance_audit(state: AIOState, layer: SafetyGovernance, streaming_manager: Any = None) -> AIOState:
    state = layer.audit(state)
    state = layer.check_compliance(state)
    state = layer.governance_vote(state)
    state = layer.record_decision(state)
    return state


# Layer 12 nodes

def node_cognitive_immune_scan(state: AIOState, layer: CognitiveImmuneSystem, streaming_manager: Any = None) -> AIOState:
    state = layer.scan(state)
    state = layer.detect_threats(state)
    state = layer.quarantine(state)
    state = layer.heal(state)
    state = layer.update_immunity(state)
    return state


# Neuro-Symbolic Mandate nodes

def node_neuro_symbolic_parse(state: AIOState, layer: NeuroSymbolicMandate, streaming_manager: Any = None) -> AIOState:
    return layer.parse_to_logic(state)


def node_neuro_symbolic_infer(state: AIOState, layer: NeuroSymbolicMandate, streaming_manager: Any = None) -> AIOState:
    return layer.infer(state)


def node_neuro_symbolic_ground(state: AIOState, layer: NeuroSymbolicMandate, streaming_manager: Any = None) -> AIOState:
    return layer.ground_knowledge(state)


def node_neuro_symbolic_verify(state: AIOState, layer: NeuroSymbolicMandate, streaming_manager: Any = None) -> AIOState:
    return layer.verify_constraints(state)


def node_neuro_symbolic_synthesize(state: AIOState, layer: NeuroSymbolicMandate, streaming_manager: Any = None) -> AIOState:
    return layer.synthesize(state)
