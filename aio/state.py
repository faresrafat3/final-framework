from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, TypedDict

from .config.deps import DEFAULT_MAX_RETRIES


class AIOState(TypedDict, total=False):
    session_id: str
    trace_id: str
    turn: int
    raw_input: str
    intent: Optional[str]
    context_window: List[Dict[str, Any]]
    context_budget: int
    attention_map: Dict[str, float]
    working_memory: List[Dict[str, Any]]
    long_term_memory: List[Dict[str, Any]]
    memory_confidence: float
    plan: Optional[str]
    hierarchical_plan: Optional[Dict[str, Any]]
    lookahead_result: Optional[Dict[str, Any]]
    fact_augmented_plan: Optional[str]
    pitfall_analysis: Optional[Dict[str, Any]]
    spiral_tree: Optional[Dict[str, Any]]
    mars_reflection: Optional[str]
    maci_meta_plan: Optional[str]
    vmao_dag: Optional[List[Dict[str, Any]]]
    curiosity_score: float
    novelty_map: Dict[str, float]
    information_gaps: List[str]
    verification_result: Dict[str, Any]
    tool_necessity_score: float
    tool_policy_channels: Dict[str, Any]
    tool_prompt_optimization: Dict[str, Any]
    sandbox_result: Optional[Dict[str, Any]]
    tool_analytics: Dict[str, Any]
    execution_result: Dict[str, Any]
    failure_state: str
    failure_count: int
    retry_budget: int
    safety_violations: List[Dict[str, Any]]
    output: Optional[str]
    error: Optional[str]
    metrics: Dict[str, Any]
    # Layer 9 — Self-Evolution
    self_evolution_report: Optional[Dict[str, Any]]
    performance_snapshot: Optional[Dict[str, Any]]
    suggested_config_delta: Optional[List[Dict[str, Any]]]
    # Layer 10 — Multi-Agent Coordination
    coordination_plan: Optional[Dict[str, Any]]
    agent_outputs: Optional[Dict[str, Any]]
    consensus_score: Optional[float]
    # Layer 11 — Safety & Governance
    audit_trail: Optional[List[Dict[str, Any]]]
    governance_result: Optional[Dict[str, Any]]
    compliance_violations: Optional[List[Dict[str, Any]]]
    # Layer 12 — Cognitive Immune System
    immune_status: Optional[str]
    anomaly_score: Optional[float]
    quarantined_ids: Optional[List[str]]
    healing_actions: Optional[List[Dict[str, Any]]]
    threat_patterns_detected: Optional[List[Dict[str, Any]]]
    learned_anomaly_score: Optional[float]


def make_initial_state(raw_input: str = "", session_id: Optional[str] = None) -> AIOState:
    sid = session_id or str(uuid.uuid4())
    trace_id = str(uuid.uuid4()).replace("-", "")
    return {
        "session_id": sid,
        "trace_id": trace_id,
        "turn": 0,
        "raw_input": raw_input,
        "intent": None,
        "context_window": [],
        "context_budget": 4096,
        "attention_map": {},
        "working_memory": [],
        "long_term_memory": [],
        "memory_confidence": 0.0,
        "plan": None,
        "hierarchical_plan": None,
        "lookahead_result": None,
        "fact_augmented_plan": None,
        "pitfall_analysis": None,
        "spiral_tree": None,
        "mars_reflection": None,
        "maci_meta_plan": None,
        "vmao_dag": None,
        "curiosity_score": 0.0,
        "novelty_map": {},
        "information_gaps": [],
        "verification_result": {},
        "tool_necessity_score": 0.0,
        "tool_policy_channels": {},
        "tool_prompt_optimization": {},
        "sandbox_result": None,
        "tool_analytics": {},
        "execution_result": {},
        "failure_state": "HEALTHY",
        "failure_count": 0,
        "retry_budget": DEFAULT_MAX_RETRIES,
        "safety_violations": [],
        "output": None,
        "error": None,
        "metrics": {},
        "self_evolution_report": None,
        "performance_snapshot": None,
        "suggested_config_delta": None,
        "coordination_plan": None,
        "agent_outputs": None,
        "consensus_score": None,
        "audit_trail": None,
        "governance_result": None,
        "compliance_violations": None,
        "immune_status": None,
        "anomaly_score": None,
        "quarantined_ids": None,
        "healing_actions": None,
        "threat_patterns_detected": None,
        "learned_anomaly_score": None,
        }
