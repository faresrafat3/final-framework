from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config.models import AIOConfig
    from ..layers.context import ContextManager

from langgraph.graph import END

from ..state import AIOState


def route_memory_confidence(state: AIOState) -> str:
    confidence = state.get("memory_confidence", 0.0)
    if confidence < 0.7:
        return "memory_encode"
    return "curiosity_intrinsic"


def route_verification(state: AIOState) -> str:
    passed = state.get("verification_result", {}).get("passed", False)
    return "gstep_evaluate" if passed else "debug_and_replan"


def route_failure(state: AIOState) -> str:
    classification = state.get("metrics", {}).get("failure_classification", "transient")
    if classification == "transient":
        budget = state.get("retry_budget", 0)
        if budget > 0:
            return "retry_with_backoff"
        return "escalate"
    elif classification == "permanent":
        return "escalate"
    return "graceful_degrade"


def route_shield(state: AIOState) -> str:
    return "escalate" if state.get("safety_violations") else "memory_retrieve"


def route_ppa(state: AIOState) -> str:
    analysis = state.get("pitfall_analysis", {})
    return "escalate" if not analysis.get("safe_to_proceed", True) else "spiral_mcts"


def route_gstep(state: AIOState) -> str:
    rejected = state.get("metrics", {}).get("gstep_rejected", False)
    return "finalize_output" if rejected else "hdpo_optimize"


def route_post_execution(state: AIOState) -> str:
    exec_res = state.get("execution_result", {})
    return "finalize_output" if exec_res.get("success") else "failure_assess"


def route_context_priority(state: AIOState, ctx_mgr: "ContextManager") -> str:
    target = ctx_mgr.route_attention(state)
    if target == "memory":
        return "memory_retrieve"
    if target == "verify":
        return "verify_plan"
    if target == "execute":
        return "gstep_evaluate"
    return "memory_retrieve"


def route_multi_agent(state: AIOState, config: "AIOConfig") -> str:
    if not config.enable_priority_3 or not config.multi_agent.enable:
        return "hiplan"
    intent = state.get("intent", "general")
    plan = state.get("plan", "")
    if intent in {"coding", "analysis"} or len(plan) > 200:
        return "multi_agent_decompose"
    return "hiplan"


def route_safety_governance(state: AIOState, config: "AIOConfig") -> str:
    if not config.enable_priority_3 or not config.safety_governance.enable:
        return "verify_plan"
    return "safety_governance_audit"


def route_hitl(state: AIOState, config: "AIOConfig") -> str:
    if not config.hitl.enable:
        return "execute_action"
    status = state.get("hitl_status")
    if status == "pending":
        return "hitl_wait"
    if status == "rejected":
        return "escalate"
    return "execute_action"


def route_post_finalize(state: AIOState, config: "AIOConfig") -> str:
    if not config.enable_priority_3:
        return END
    if config.hitl.enable or config.self_evolution.enable:
        return "feedback_collect"
    return END


def route_self_evolution(state: AIOState, config: "AIOConfig") -> str:
    if config.hitl.enable:
        return "escalation_policy_eval"
    return END


def route_escalation_policy(state: AIOState, config: "AIOConfig") -> str:
    if state.get("escalation_reason"):
        return "feedback_loop_replay"
    return "feedback_loop_replay"


def route_neuro_symbolic(state: AIOState, config: "AIOConfig") -> str:
    if not config.neuro_symbolic.enable:
        return "verify_plan"
    verdict = state.get("neuro_symbolic_verdict", {})
    if verdict.get("passed") is False:
        return "debug_and_replan"
    return "neuro_symbolic_synthesize"


def route_post_neuro_symbolic(state: AIOState, config: "AIOConfig") -> str:
    if not config.neuro_symbolic.enable:
        return "gstep_evaluate"
    return "gstep_evaluate"
