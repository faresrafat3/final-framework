from __future__ import annotations

from ..layers.context import ContextManager
from ..layers.memory import MemoryBridge
from ..layers.planning import PlanningLayer
from ..layers.curiosity import CuriosityEngine
from ..layers.verification import Verifier
from ..layers.tool_optimizer import ToolOptimizer
from ..layers.tool_gate import ToolGate
from ..layers.failure_recovery import FailureRecovery
from ..layers.self_evolution import SelfEvolutionLayer
from ..layers.multi_agent import MultiAgentCoordinator
from ..layers.safety_governance import SafetyGovernance
from ..layers.cognitive_immune import CognitiveImmuneSystem
from ..state import AIOState


# Layer 1 nodes

def node_context_ingest(state: AIOState, ctx_mgr: ContextManager) -> AIOState:
    return ctx_mgr.ingest(state)


def node_context_sculpt(state: AIOState, ctx_mgr: ContextManager) -> AIOState:
    return ctx_mgr.sculpt(state)


# Layer 2 nodes

def node_memory_retrieve(state: AIOState, mem: MemoryBridge) -> AIOState:
    return mem.retrieve(state)


def node_memory_encode(state: AIOState, mem: MemoryBridge) -> AIOState:
    return mem.encode(state)


def node_memory_verify(state: AIOState, mem: MemoryBridge) -> AIOState:
    return mem.verify(state)


def node_memory_store(state: AIOState, mem: MemoryBridge) -> AIOState:
    return mem.store(state)


def node_memory_consolidate(state: AIOState, mem: MemoryBridge) -> AIOState:
    return mem.consolidate(state)


# Planning stub

def node_plan_generate(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.generate_plan(state)


# Layer 3 nodes

def node_maci_select(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_maci(state)


def node_hiplan(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_hiplan(state)


def node_flare(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_flare(state)


def node_lwm_augment(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_lwm(state)


def node_ppa_analyze(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_ppa(state)


def node_spiral_mcts(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_spiral(state)


def node_mars_reflect(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_mars(state)


def node_vmao_decompose(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_vmao_decompose(state)


# Layer 4 nodes

def node_curiosity_intrinsic(state: AIOState, curiosity: CuriosityEngine) -> AIOState:
    return curiosity.intrinsic_reward(state)


def node_curiosity_seek(state: AIOState, curiosity: CuriosityEngine) -> AIOState:
    return curiosity.active_seek(state)


def node_curiosity_serendipity(state: AIOState, curiosity: CuriosityEngine) -> AIOState:
    return curiosity.serendipity(state)


def node_curiosity_counterfactual(state: AIOState, curiosity: CuriosityEngine) -> AIOState:
    return curiosity.counterfactual(state)


def node_curiosity_umwelt(state: AIOState, curiosity: CuriosityEngine) -> AIOState:
    return curiosity.umwelt_constraints(state)


# Layer 5 nodes

def node_verify_plan(state: AIOState, verifier: Verifier) -> AIOState:
    state = verifier.critique(state)
    state = verifier.judge(state)
    state = verifier.score(state)
    state = verifier.debug(state)
    return state


def node_debug_and_replan(state: AIOState, verifier: Verifier) -> AIOState:
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

def node_gstep_evaluate(state: AIOState, toolopt: ToolOptimizer) -> AIOState:
    return toolopt.gstep_evaluate(state)


def node_hdpo_optimize(state: AIOState, toolopt: ToolOptimizer) -> AIOState:
    return toolopt.hdpo_optimize(state)


def node_jtpro_optimize(state: AIOState, toolopt: ToolOptimizer) -> AIOState:
    return toolopt.jtpro_optimize(state)


def node_sandbox_execute(state: AIOState, toolopt: ToolOptimizer, toolgate: ToolGate) -> AIOState:
    return toolopt.sandbox_execute(state, toolgate)


def node_analytics_record(state: AIOState, toolopt: ToolOptimizer) -> AIOState:
    return toolopt.analytics_record(state)


# Layer 7 node

def node_execute_action(state: AIOState, toolgate: ToolGate) -> AIOState:
    return toolgate.execute(state)


# Layer 8 nodes

def node_failure_assess(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.assess(state)


def node_retry_with_backoff(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.retry(state)


def node_escalate(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.escalate(state)


def node_graceful_degrade(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.degrade(state)


def node_neuroshield(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.shield(state)


def node_failure_learn(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.learn(state)


def node_finalize_output(state: AIOState) -> AIOState:
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

def node_self_evolution_analyze(state: AIOState, layer: SelfEvolutionLayer) -> AIOState:
    state = layer.analyze(state)
    state = layer.generate_report(state)
    state = layer.suggest_improvements(state)
    state = layer.apply_deltas(state)
    return state


# Layer 10 nodes

def node_multi_agent_decompose(state: AIOState, layer: MultiAgentCoordinator) -> AIOState:
    return layer.decompose(state)


def node_multi_agent_dispatch(state: AIOState, layer: MultiAgentCoordinator) -> AIOState:
    return layer.dispatch(state)


def node_multi_agent_aggregate(state: AIOState, layer: MultiAgentCoordinator) -> AIOState:
    return layer.aggregate(state)


def node_multi_agent_synthesize(state: AIOState, layer: MultiAgentCoordinator) -> AIOState:
    return layer.synthesize(state)


# Layer 11 nodes

def node_safety_governance_audit(state: AIOState, layer: SafetyGovernance) -> AIOState:
    state = layer.audit(state)
    state = layer.check_compliance(state)
    state = layer.governance_vote(state)
    state = layer.record_decision(state)
    return state


# Layer 12 nodes

def node_cognitive_immune_scan(state: AIOState, layer: CognitiveImmuneSystem) -> AIOState:
    state = layer.scan(state)
    state = layer.detect_threats(state)
    state = layer.quarantine(state)
    state = layer.heal(state)
    state = layer.update_immunity(state)
    return state
