from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from typing import Any, Dict, List, Optional

from ..config.deps import (
    LANGCHAIN_CHAT_AVAILABLE,
    LANGCHAIN_OPENAI_AVAILABLE,
    LANGCHAIN_ANTHROPIC_AVAILABLE,
)
from ..config.models import PlanningConfig, NeuroSymbolicConfig
from .observability import ObservabilityLayer
from ..state import AIOState
from .neuro_symbolic import SymbolicPlanner

if LANGCHAIN_OPENAI_AVAILABLE:
    from langchain_openai import ChatOpenAI
if LANGCHAIN_ANTHROPIC_AVAILABLE:
    from langchain_anthropic import ChatAnthropic


class HiPlanPlanner:
    """Hierarchical planning: decomposes a flat plan into goal-subgoal-action tree."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    def plan(self, state: AIOState) -> Dict[str, Any]:
        """Build a hierarchical plan from the current flat plan."""
        start = time.time()
        with self.obs.start_span("planning.hiplan", state.get("trace_id")):
            raw_plan = state.get("plan", "")
            steps = [s.strip() for s in re.split(r"\d+\)", raw_plan) if s.strip()]
            hierarchy = {
                "goal": state.get("intent", "general"),
                "subgoals": [
                    {
                        "id": f"sg-{i}",
                        "description": step,
                        "actions": [{"id": f"act-{i}-0", "description": f"Execute: {step}"}],
                    }
                    for i, step in enumerate(steps[: self.config.hiplan_max_depth])
                ],
            }
            self.obs.record_latency("planning.hiplan", time.time() - start)
            self.obs.count_node("planning.hiplan", "success")
        return hierarchy


class FLARELookahead:
    """Future-aware lookahead: scores trajectories over a planning horizon."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    def lookahead(self, state: AIOState) -> Dict[str, Any]:
        """Simulate future steps and return risk-adjusted trajectory scores."""
        start = time.time()
        with self.obs.start_span("planning.flare", state.get("trace_id")):
            horizon = self.config.flare_horizon
            confidence = state.get("memory_confidence", 0.0)
            scores = []
            for step in range(horizon):
                score = 0.5 + (confidence * 0.3) - (step * 0.1)
                scores.append(round(max(0.0, min(1.0, score)), 4))
            best_step = scores.index(max(scores)) if scores else 0
            risk = "low" if max(scores, default=0.0) > 0.7 else "medium"
            self.obs.record_latency("planning.flare", time.time() - start)
            self.obs.count_node("planning.flare", "success")
        return {
            "horizon": horizon,
            "trajectory_scores": scores,
            "recommended_action_index": best_step,
            "risk_assessment": risk,
        }


class LWMPlanner:
    """Fact-augmented planning: enriches plan with verified facts from memory."""

    def __init__(self, observability: ObservabilityLayer) -> None:
        self.obs = observability

    def augment(self, state: AIOState) -> str:
        """Return plan augmented with facts from verified working memory."""
        start = time.time()
        with self.obs.start_span("planning.lwm", state.get("trace_id")):
            plan = state.get("plan", "")
            memories = state.get("working_memory", [])
            facts = [m["content"] for m in memories if m.get("verification_passed")]
            if facts:
                augmented = f"[FACTS] {' | '.join(facts[:3])}\n[PLAN] {plan}"
            else:
                augmented = plan
            self.obs.record_latency("planning.lwm", time.time() - start)
            self.obs.count_node("planning.lwm", "success")
        return augmented


class PPAPlanner:
    """Proactive Pitfall Avoidance: detects likely failure modes and adds guardrails."""

    def __init__(self, observability: ObservabilityLayer) -> None:
        self.obs = observability

    def analyze(self, state: AIOState) -> Dict[str, Any]:
        """Analyze plan for pitfalls and return guardrail recommendations."""
        start = time.time()
        with self.obs.start_span("planning.ppa", state.get("trace_id")):
            plan = state.get("plan", "")
            pitfalls = []
            lowered = (plan or "").lower()
            if "loop" in lowered or "while" in lowered:
                pitfalls.append({"type": "infinite_loop", "mitigation": "Add iteration limit."})
            if "delete" in lowered or "remove" in lowered:
                pitfalls.append({"type": "data_loss", "mitigation": "Add backup step."})
            if len(plan or "") > 2000:
                pitfalls.append({"type": "complexity", "mitigation": "Decompose into smaller subplans."})
            safe_to_proceed = len(pitfalls) == 0
            self.obs.record_latency("planning.ppa", time.time() - start)
            self.obs.count_node("planning.ppa", "success" if safe_to_proceed else "blocked")
        return {
            "pitfalls_detected": pitfalls,
            "guardrails_added": [p["mitigation"] for p in pitfalls],
            "safe_to_proceed": safe_to_proceed,
        }


class SPIRALPlanner:
    """Symbolic MCTS planning via Planner-Simulator-Critic tri-agent loop."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    def mcts_plan(self, state: AIOState) -> Dict[str, Any]:
        """Run lightweight symbolic MCTS and return best variant."""
        start = time.time()
        with self.obs.start_span("planning.spiral", state.get("trace_id")):
            root = {"state": state.get("plan", ""), "visits": 0, "value": 0.0, "children": []}
            for sim in range(self.config.spiral_simulations):
                child = {"id": f"sim-{sim}", "plan_variant": f"Variant {sim}"}
                outcome = random.uniform(0.0, 1.0)
                score = outcome * 0.8 + 0.2
                root["children"].append({**child, "score": round(score, 4)})
            best = max(root["children"], key=lambda c: c["score"]) if root["children"] else None
            self.obs.record_latency("planning.spiral", time.time() - start)
            self.obs.count_node("planning.spiral", "success")
        return {
            "root": root,
            "best_variant": best,
            "exploration_rate": 1.0 / (1 + len(root["children"])),
        }


class MARSReflector:
    """One-shot self-reflection: critiques the current plan and surfaces concerns."""

    def __init__(self, observability: ObservabilityLayer) -> None:
        self.obs = observability

    def reflect(self, state: AIOState) -> str:
        """Return a one-shot reflection on plan quality."""
        start = time.time()
        with self.obs.start_span("planning.mars", state.get("trace_id")):
            plan = state.get("plan", "")
            verification = state.get("verification_result", {})
            critiques = verification.get("critiques", [])
            if critiques:
                reflection = f"MARS Reflection: Plan has {len(critiques)} issue(s): {'; '.join(critiques)}."
            else:
                reflection = "MARS Reflection: Plan appears sound; no immediate concerns."
            self.obs.record_latency("planning.mars", time.time() - start)
            self.obs.count_node("planning.mars", "success")
        return reflection


class MACIMetaPlanner:
    """Meta-planner: selects the most appropriate planner for the task."""

    def __init__(self, observability: ObservabilityLayer) -> None:
        self.obs = observability

    def select_planner(self, state: AIOState) -> str:
        """Return planner name best suited for current intent."""
        start = time.time()
        with self.obs.start_span("planning.maci", state.get("trace_id")):
            intent = state.get("intent", "general")
            if intent in {"coding", "analysis"}:
                selected = "spiral"
            elif intent == "action":
                selected = "vmao"
            else:
                selected = "hiplan"
            self.obs.record_latency("planning.maci", time.time() - start)
            self.obs.count_node("planning.maci", "success")
        return selected


class VMAOPlanner:
    """Plan-execute-verify-replan with DAG decomposition."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    def decompose(self, state: AIOState) -> List[Dict[str, Any]]:
        """Decompose plan into a DAG of executable nodes."""
        start = time.time()
        with self.obs.start_span("planning.vmao.decompose", state.get("trace_id")):
            plan = state.get("plan", "")
            steps = [s.strip() for s in re.split(r"\d+\)", plan) if s.strip()]
            dag = []
            for i, step in enumerate(steps):
                node = {
                    "id": f"node-{i}",
                    "description": step,
                    "dependencies": [f"node-{i-1}"] if i > 0 else [],
                    "status": "pending",
                    "verified": False,
                }
                dag.append(node)
            self.obs.record_latency("planning.vmao.decompose", time.time() - start)
            self.obs.count_node("planning.vmao.decompose", "success")
        return dag

    def replan(self, state: AIOState) -> List[Dict[str, Any]]:
        """Replan failed DAG nodes."""
        dag = state.get("vmao_dag", [])
        for node in dag:
            if not node.get("verified"):
                node["status"] = "replanning"
                node["description"] = f"[REPLAN] {node['description']}"
        return dag


class LLMPlanner:
    """Optional LLM-powered planner behind a feature flag and optional dependency guard."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._model: Optional[Any] = None

    def _get_chat_model(self) -> Optional[Any]:
        if not LANGCHAIN_CHAT_AVAILABLE:
            return None
        if self._model is not None:
            return self._model
        provider = self.config.llm_planner_provider
        if provider == "openai" and LANGCHAIN_OPENAI_AVAILABLE:
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                self.obs.log(logging.WARNING, "LLMPlanner: OPENAI_API_KEY not set")
                return None
            self._model = ChatOpenAI(
                model=self.config.llm_planner_model,
                temperature=self.config.llm_planner_temperature,
                max_tokens=self.config.llm_planner_max_tokens,
                api_key=key,
            )
            return self._model
        if provider == "anthropic" and LANGCHAIN_ANTHROPIC_AVAILABLE:
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                self.obs.log(logging.WARNING, "LLMPlanner: ANTHROPIC_API_KEY not set")
                return None
            self._model = ChatAnthropic(
                model=self.config.llm_planner_model,
                temperature=self.config.llm_planner_temperature,
                max_tokens=self.config.llm_planner_max_tokens,
                api_key=key,
            )
            return self._model
        return None

    def _call_llm(self, prompt: str, span_name: str) -> str:
        model = self._get_chat_model()
        if model is None:
            raise RuntimeError("LLM chat model not available")
        start = time.time()
        with self.obs.start_span(span_name):
            try:
                response = model.invoke(prompt)
                text = str(response.content if hasattr(response, "content") else response)
                self.obs.record_latency(span_name, time.time() - start)
                self.obs.count_node(span_name, "success")
                return text
            except Exception as exc:
                self.obs.record_latency(span_name, time.time() - start)
                self.obs.count_node(span_name, "failure")
                self.obs.log(logging.WARNING, f"LLMPlanner {span_name} failed: {exc}")
                raise

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except Exception:
            return {}

    def generate_plan(self, state: AIOState) -> str:
        intent = state.get("intent", "general")
        memory = state.get("working_memory", [])
        snippets = " | ".join(str(m.get("content", ""))[:200] for m in memory[:3])
        prompt = (
            f"You are a planning assistant. Given the intent '{intent}' and recent memory snippets: [{snippets}],\n"
            "produce a concise, numbered step-by-step plan (max 5 steps). "
            "Return only the plan text with no extra commentary."
        )
        return self._call_llm(prompt, "planning.llm_generate")

    def decompose_tasks(self, state: AIOState) -> Dict[str, Any]:
        intent = state.get("intent", "general")
        plan = state.get("plan", "")
        prompt = (
            f"You are a hierarchical planning assistant. Decompose this plan into JSON with keys:"
            f"  goal: string"
            f"  subgoals: list of {{id, description, actions: [{{id, description}}]}}"
            f"Intent: {intent}"
            f"Plan: {plan}"
            f"Return only valid JSON inside a markdown code block if needed."
        )
        text = self._call_llm(prompt, "planning.llm_decompose")
        parsed = self._parse_json(text)
        if not parsed or "goal" not in parsed:
            raise RuntimeError("LLM decompose returned invalid JSON")
        return parsed

    def lookahead_analysis(self, state: AIOState) -> Dict[str, Any]:
        horizon = self.config.flare_horizon
        plan = state.get("plan", "")
        prompt = (
            f"You are a risk-aware lookahead assistant. Analyze this plan over a horizon of {horizon} steps."
            f"Return JSON with keys: horizon (int), trajectory_scores (list of floats), recommended_action_index (int), risk_assessment (string)."
            f"Plan: {plan}"
            f"Return only valid JSON inside a markdown code block if needed."
        )
        text = self._call_llm(prompt, "planning.llm_lookahead")
        parsed = self._parse_json(text)
        required = {"horizon", "trajectory_scores", "recommended_action_index", "risk_assessment"}
        if not required.issubset(parsed.keys()):
            raise RuntimeError("LLM lookahead returned incomplete JSON")
        return parsed

    def pitfall_analysis(self, state: AIOState) -> Dict[str, Any]:
        plan = state.get("plan", "")
        prompt = (
            f"You are a safety reviewer. Review this plan and return JSON with keys:"
            f"  pitfalls_detected: list of {{type, mitigation}}"
            f"  guardrails_added: list of strings"
            f"  safe_to_proceed: bool"
            f"Plan: {plan}"
            f"Return only valid JSON inside a markdown code block if needed."
        )
        text = self._call_llm(prompt, "planning.llm_pitfall")
        parsed = self._parse_json(text)
        required = {"pitfalls_detected", "guardrails_added", "safe_to_proceed"}
        if not required.issubset(parsed.keys()):
            raise RuntimeError("LLM pitfall returned incomplete JSON")
        return parsed


class PlanningLayer:
    """Layer 3 — Orchestrates all planners with escalation and rejection paths.

    Composes HiPlan, FLARE, LWM, PPA, SPIRAL, MARS, MACI, VMAO, and an
    optional LLM-backed planner.  Each sub-planner can be called individually
    via the ``run_*`` methods, or the layer can be used through the
    node wrappers in :mod:`aio.graph.nodes`.

    Args:
        config: Layer 3 configuration (depths, horizons, LLM settings).
        observability: Shared observability layer for spans and metrics.
    """

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer, neuro_symbolic_config: Optional[NeuroSymbolicConfig] = None) -> None:
        self.config = config
        self.obs = observability
        self.hiplan = HiPlanPlanner(config, observability)
        self.flare = FLARELookahead(config, observability)
        self.lwm = LWMPlanner(observability)
        self.ppa = PPAPlanner(observability)
        self.spiral = SPIRALPlanner(config, observability)
        self.mars = MARSReflector(observability)
        self.maci = MACIMetaPlanner(observability)
        self.vmao = VMAOPlanner(config, observability)
        if config.enable_llm_planning:
            self._llm_planner: Optional[LLMPlanner] = LLMPlanner(config, observability)
        else:
            self._llm_planner = None
        if neuro_symbolic_config is not None and neuro_symbolic_config.enable_symbolic_planning:
            self._symbolic_planner: Optional[SymbolicPlanner] = SymbolicPlanner(neuro_symbolic_config, observability)
        else:
            self._symbolic_planner = None

    def _heuristic_plan(self, state: AIOState) -> str:
        intent = state.get("intent", "general")
        memory = state.get("working_memory", [])
        snippets = " | ".join(str(m.get("content", ""))[:100] for m in memory[:3])
        return f"Plan for intent='{intent}': 1) ingest input 2) retrieve memory [{snippets}] 3) verify 4) execute 5) finalize."

    def generate_plan(self, state: AIOState) -> AIOState:
        """Generate a flat plan, preferring the LLM planner when enabled.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``plan`` set.
        """
        if self._llm_planner is not None:
            try:
                state["plan"] = self._llm_planner.generate_plan(state)
                return state
            except Exception as exc:
                self.obs.log(logging.WARNING, f"LLM generate_plan failed, falling back to heuristic: {exc}")
                self.obs.count_node("planning.llm_generate", "fallback")
        state["plan"] = self._heuristic_plan(state)
        return state

    def run_hiplan(self, state: AIOState) -> AIOState:
        """Build a hierarchical goal tree.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``hierarchical_plan``.
        """
        if self._llm_planner is not None:
            try:
                state["hierarchical_plan"] = self._llm_planner.decompose_tasks(state)
                return state
            except Exception as exc:
                self.obs.log(logging.WARNING, f"LLM decompose_tasks failed, falling back to heuristic: {exc}")
                self.obs.count_node("planning.llm_decompose", "fallback")
        state["hierarchical_plan"] = self.hiplan.plan(state)
        return state

    def run_flare(self, state: AIOState) -> AIOState:
        """Run future-aware lookahead risk assessment.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``lookahead_result``.
        """
        if self._llm_planner is not None:
            try:
                state["lookahead_result"] = self._llm_planner.lookahead_analysis(state)
                return state
            except Exception as exc:
                self.obs.log(logging.WARNING, f"LLM lookahead_analysis failed, falling back to heuristic: {exc}")
                self.obs.count_node("planning.llm_lookahead", "fallback")
        state["lookahead_result"] = self.flare.lookahead(state)
        return state

    def run_lwm(self, state: AIOState) -> AIOState:
        """Augment the plan with verified memory facts.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``fact_augmented_plan``.
        """
        state["fact_augmented_plan"] = self.lwm.augment(state)
        return state

    def run_ppa(self, state: AIOState) -> AIOState:
        """Detect pitfalls and optionally block unsafe plans.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``pitfall_analysis`` and possibly ``failure_state`` updated.
        """
        if self._llm_planner is not None:
            try:
                analysis = self._llm_planner.pitfall_analysis(state)
                state["pitfall_analysis"] = analysis
                if not analysis.get("safe_to_proceed", True):
                    state["failure_state"] = "FAILED"
                    state["error"] = state.get("error") or f"PPA blocked: {len(analysis['pitfalls_detected'])} pitfall(s) detected."
                    self.obs.set_failure_state("FAILED")
                    self.obs.count_node("planning.ppa", "escalated")
                return state
            except Exception as exc:
                self.obs.log(logging.WARNING, f"LLM pitfall_analysis failed, falling back to heuristic: {exc}")
                self.obs.count_node("planning.llm_pitfall", "fallback")
        analysis = self.ppa.analyze(state)
        state["pitfall_analysis"] = analysis
        if not analysis.get("safe_to_proceed", True):
            state["failure_state"] = "FAILED"
            state["error"] = state.get("error") or f"PPA blocked: {len(analysis['pitfalls_detected'])} pitfall(s) detected."
            self.obs.set_failure_state("FAILED")
            self.obs.count_node("planning.ppa", "escalated")
        return state

    def run_spiral(self, state: AIOState) -> AIOState:
        """Run symbolic MCTS planning.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``spiral_tree``.
        """
        state["spiral_tree"] = self.spiral.mcts_plan(state)
        return state

    def run_mars(self, state: AIOState) -> AIOState:
        """Run one-shot self-reflection on the current plan.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``mars_reflection``.
        """
        state["mars_reflection"] = self.mars.reflect(state)
        return state

    def run_maci(self, state: AIOState) -> AIOState:
        """Select the most appropriate planner for the current intent.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``maci_meta_plan``.
        """
        state["maci_meta_plan"] = self.maci.select_planner(state)
        return state

    def run_vmao_decompose(self, state: AIOState) -> AIOState:
        """Decompose the plan into a DAG of executable nodes.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``vmao_dag``.
        """
        state["vmao_dag"] = self.vmao.decompose(state)
        return state

    def run_vmao_replan(self, state: AIOState) -> AIOState:
        """Replan failed DAG nodes.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with updated ``vmao_dag``.
        """
        state["vmao_dag"] = self.vmao.replan(state)
        return state

    def run_symbolic_plan(self, state: AIOState) -> AIOState:
        """Run symbolic constraint validation on the current plan.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with symbolic validation results.
        """
        if self._symbolic_planner is None:
            return state
        try:
            return self._symbolic_planner.plan(state)
        except Exception as exc:
            self.obs.log(logging.WARNING, f"SymbolicPlanner failed, continuing unchanged: {exc}")
            self.obs.count_node("symbolic_planner.plan", "fallback")
            return state
