from __future__ import annotations

import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..config.deps import LANGCHAIN_CHAT_AVAILABLE, Z3_AVAILABLE, ORTOOLS_AVAILABLE
from ..config.models import NeuroSymbolicConfig
from .observability import ObservabilityLayer
from ..state import AIOState

if LANGCHAIN_CHAT_AVAILABLE:
    try:
        from langchain_openai import ChatOpenAI
    except Exception:
        ChatOpenAI = None  # type: ignore[misc,assignment]
    try:
        from langchain_anthropic import ChatAnthropic
    except Exception:
        ChatAnthropic = None  # type: ignore[misc,assignment]
else:
    ChatOpenAI = None  # type: ignore[misc,assignment]
    ChatAnthropic = None  # type: ignore[misc,assignment]


class SymbolicRule:
    """A single Horn-like rule:  if premises then conclusion."""

    def __init__(self, name: str, premises: List[str], conclusion: str, weight: float = 1.0) -> None:
        self.name = name
        self.premises = premises
        self.conclusion = conclusion
        self.weight = weight


class SymbolicEngine:
    """Lightweight forward-chaining inference engine over :class:`SymbolicRule`."""

    def __init__(self, rules: Optional[List[SymbolicRule]] = None) -> None:
        self.rules = rules or []
        self._facts: set[str] = set()

    def add_fact(self, fact: str) -> None:
        self._facts.add(fact.lower().strip())

    def reset(self) -> None:
        self._facts.clear()

    def infer(self, max_depth: int = 5) -> Dict[str, Any]:
        """Run forward chaining and return derived facts with provenance."""
        derived: List[Dict[str, Any]] = []
        for _ in range(max_depth):
            progressed = False
            for rule in self.rules:
                if all(p.lower().strip() in self._facts for p in rule.premises):
                    conc = rule.conclusion.lower().strip()
                    if conc not in self._facts:
                        self._facts.add(conc)
                        derived.append({"rule": rule.name, "conclusion": conc, "weight": rule.weight})
                        progressed = True
            if not progressed:
                break
        return {"facts": sorted(self._facts), "derived": derived}


class KnowledgeGraph:
    """In-memory entity-relationship graph for symbolic grounding."""

    def __init__(self) -> None:
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: Dict[str, List[Tuple[str, str, float]]] = {}

    def add_entity(self, entity_id: str, entity_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        self._nodes[entity_id] = {"type": entity_type, "properties": properties or {}}
        self._edges.setdefault(entity_id, [])

    def add_relation(self, source: str, relation: str, target: str, confidence: float = 1.0) -> None:
        self._edges.setdefault(source, []).append((relation, target, confidence))

    def query(self, entity_id: str, relation: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for rel, tgt, conf in self._edges.get(entity_id, []):
            if relation is None or rel == relation:
                results.append({"relation": rel, "target": tgt, "confidence": conf})
        return results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": self._nodes,
            "relations": {k: [{"relation": r, "target": t, "confidence": c} for r, t, c in v] for k, v in self._edges.items()},
        }


class FormalVerifier:
    """Deterministic constraint checker (bounds, schema, temporal)."""

    def __init__(self, config: NeuroSymbolicConfig) -> None:
        self.config = config

    def check_bounds(self, plan: str) -> List[Dict[str, Any]]:
        """Check that the plan length and step count are within configured bounds."""
        checks = []
        checks.append({
            "rule": "max_plan_length",
            "passed": len(plan) <= self.config.max_plan_length,
            "limit": self.config.max_plan_length,
            "actual": len(plan),
        })
        steps = [s for s in re.split(r"\d+\)", plan) if s.strip()]
        checks.append({
            "rule": "max_steps",
            "passed": len(steps) <= self.config.max_inference_depth,
            "limit": self.config.max_inference_depth,
            "actual": len(steps),
        })
        return checks

    def check_schema(self, symbolic_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate that the symbolic plan has required keys."""
        checks = []
        required = {"goal", "steps"}
        keys = set(symbolic_plan.keys())
        checks.append({
            "rule": "required_keys",
            "passed": required.issubset(keys),
            "missing": sorted(required - keys),
        })
        return checks

    def check_temporal(self, steps: List[str]) -> List[Dict[str, Any]]:
        """Detect temporal contradictions (e.g., a before b and b before a)."""
        checks = []
        contradictions = []
        lowered_steps = [s.lower() for s in steps]
        for i, a in enumerate(lowered_steps):
            for j, b in enumerate(lowered_steps):
                if i < j:
                    forward = any(f"{a} before {b}" in s for s in lowered_steps)
                    reverse = any(f"{b} before {a}" in s for s in lowered_steps)
                    if forward and reverse:
                        contradictions.append((a, b))
        checks.append({
            "rule": "temporal_consistency",
            "passed": len(contradictions) == 0,
            "contradictions": contradictions,
        })
        return checks

    def verify(self, plan: str, symbolic_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Run all formal checks and return a composite verdict."""
        all_checks: List[Dict[str, Any]] = []
        all_checks.extend(self.check_bounds(plan))
        all_checks.extend(self.check_schema(symbolic_plan))
        steps = symbolic_plan.get("steps", [])
        if isinstance(steps, list):
            all_checks.extend(self.check_temporal(steps))
        passed = all(c["passed"] for c in all_checks)
        return {"passed": passed, "checks": all_checks}


# ---------------------------------------------------------------------------
# Deep Neuro-Symbolic Integration — Priority 9
# ---------------------------------------------------------------------------

@dataclass
class ConstraintModel:
    """Portable formal constraint model generated from a plan."""

    variables: Dict[str, Any] = field(default_factory=dict)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    objectives: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SolverResult:
    """Result returned by a symbolic solver backend."""

    status: str = "unknown"  # sat, unsat, unknown, error
    model: Optional[Dict[str, Any]] = None
    counterexample: Optional[Dict[str, Any]] = None
    explanation: str = ""


class SymbolicSolverBackend(ABC):
    """Abstract base for SMT/CP solver backends."""

    @abstractmethod
    def solve(self, model: ConstraintModel, timeout_ms: int = 5000) -> SolverResult:
        """Solve the constraint model and return a :class:`SolverResult`."""
        ...


class NoOpBackend(SymbolicSolverBackend):
    """Fallback backend when no solver library is installed."""

    def solve(self, model: ConstraintModel, timeout_ms: int = 5000) -> SolverResult:
        return SolverResult(status="unknown", explanation="No solver library available")


class Z3Backend(SymbolicSolverBackend):
    """Z3-based SMT solver backend."""

    def __init__(self) -> None:
        if not Z3_AVAILABLE:
            raise RuntimeError("z3 is not available")

    def solve(self, model: ConstraintModel, timeout_ms: int = 5000) -> SolverResult:
        try:
            import z3
            solver = z3.Solver()
            solver.set("timeout", timeout_ms)
            var_map: Dict[str, Any] = {}
            for name, spec in model.variables.items():
                vtype = spec.get("type", "int")
                if vtype == "bool":
                    var_map[name] = z3.Bool(name)
                elif vtype == "int":
                    lo = spec.get("low", 0)
                    hi = spec.get("high", 100)
                    var_map[name] = z3.Int(name)
                    solver.add(var_map[name] >= lo, var_map[name] <= hi)
                else:
                    var_map[name] = z3.Real(name)
            for c in model.constraints:
                ctype = c.get("type", "linear")
                if ctype == "linear":
                    expr = sum(coef * var_map.get(var, 0) for var, coef in c.get("terms", {}).items())
                    op = c.get("op", "<=")
                    rhs = c.get("rhs", 0)
                    if op == "<=":
                        solver.add(expr <= rhs)
                    elif op == ">=":
                        solver.add(expr >= rhs)
                    elif op == "==":
                        solver.add(expr == rhs)
                elif ctype == "ordering":
                    a = var_map.get(c.get("before"))
                    b = var_map.get(c.get("after"))
                    if a is not None and b is not None:
                        solver.add(a < b)
            for o in model.objectives:
                expr = sum(coef * var_map.get(var, 0) for var, coef in o.get("terms", {}).items())
                solver.maximize(expr)
            result = solver.check()
            if result == z3.sat:
                m = solver.model()
                model_dict = {str(v): str(m.evaluate(var_map[v], model_completion=True)) for v in var_map}
                return SolverResult(status="sat", model=model_dict, explanation="Plan is satisfiable")
            elif result == z3.unsat:
                return SolverResult(status="unsat", explanation="Plan constraints are unsatisfiable")
            else:
                return SolverResult(status="unknown", explanation="Z3 returned unknown (possibly timed out)")
        except Exception as exc:
            return SolverResult(status="error", explanation=f"Z3 backend error: {exc}")


class ORToolsBackend(SymbolicSolverBackend):
    """OR-Tools CP-SAT solver backend."""

    def __init__(self) -> None:
        if not ORTOOLS_AVAILABLE:
            raise RuntimeError("ortools is not available")

    def solve(self, model: ConstraintModel, timeout_ms: int = 5000) -> SolverResult:
        try:
            from ortools.sat.python import cp_model
            m = cp_model.CpModel()
            var_map: Dict[str, Any] = {}
            for name, spec in model.variables.items():
                vtype = spec.get("type", "int")
                if vtype == "bool":
                    var_map[name] = m.NewBoolVar(name)
                elif vtype == "int":
                    lo = spec.get("low", 0)
                    hi = spec.get("high", 100)
                    var_map[name] = m.NewIntVar(lo, hi, name)
                else:
                    var_map[name] = m.NewIntVar(0, 1000000, name)
            for c in model.constraints:
                ctype = c.get("type", "linear")
                if ctype == "linear":
                    expr = sum(coef * var_map.get(var, 0) for var, coef in c.get("terms", {}).items())
                    op = c.get("op", "<=")
                    rhs = c.get("rhs", 0)
                    if op == "<=":
                        m.Add(expr <= rhs)
                    elif op == ">=":
                        m.Add(expr >= rhs)
                    elif op == "==":
                        m.Add(expr == rhs)
                elif ctype == "ordering":
                    a = var_map.get(c.get("before"))
                    b = var_map.get(c.get("after"))
                    if a is not None and b is not None:
                        m.Add(a < b)
            for o in model.objectives:
                expr = sum(coef * var_map.get(var, 0) for var, coef in o.get("terms", {}).items())
                m.Maximize(expr)
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = timeout_ms / 1000.0
            status = solver.Solve(m)
            if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
                model_dict = {name: solver.Value(var_map[name]) for name in var_map}
                return SolverResult(status="sat", model=model_dict, explanation="Plan is satisfiable")
            elif status == cp_model.INFEASIBLE:
                return SolverResult(status="unsat", explanation="Plan constraints are infeasible")
            else:
                return SolverResult(status="unknown", explanation="OR-Tools returned unknown or timed out")
        except Exception as exc:
            return SolverResult(status="error", explanation=f"OR-Tools backend error: {exc}")


def _make_solver_backend(engine: str) -> SymbolicSolverBackend:
    if engine == "z3" and Z3_AVAILABLE:
        return Z3Backend()
    if engine == "ortools" and ORTOOLS_AVAILABLE:
        return ORToolsBackend()
    return NoOpBackend()


class NeuroSymbolicBridge:
    """Bidirectional translator between LLM plans and formal constraints."""

    def __init__(self, config: NeuroSymbolicConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self.backend = _make_solver_backend(config.symbolic_engine)

    def forward(self, state: AIOState) -> ConstraintModel:
        """Parse plan-related state into a :class:`ConstraintModel`."""
        start = time.time()
        with self.obs.start_span("neuro_symbolic.bridge.forward", state.get("trace_id")):
            plan = state.get("plan", "") or ""
            vmao = state.get("vmao_dag", []) or []
            ns_plan = state.get("neuro_symbolic_plan", {}) or {}
            variables: Dict[str, Any] = {}
            constraints: List[Dict[str, Any]] = []
            objectives: List[Dict[str, Any]] = []
            steps = ns_plan.get("steps", []) or []
            if not steps and plan:
                steps = [s.strip() for s in re.split(r"\d+\)", plan) if s.strip()]
            # Step count bound
            max_steps = self.config.max_inference_depth
            variables["step_count"] = {"type": "int", "low": 0, "high": max_steps}
            constraints.append({
                "type": "linear",
                "terms": {"step_count": 1},
                "op": "<=",
                "rhs": max_steps,
            })
            # Temporal ordering from VMAO DAG
            if vmao:
                for node in vmao:
                    nid = node.get("id", "")
                    if nid:
                        variables[nid] = {"type": "int", "low": 0, "high": max_steps}
                for node in vmao:
                    nid = node.get("id", "")
                    for dep in node.get("dependencies", []):
                        if nid and dep:
                            constraints.append({"type": "ordering", "before": dep, "after": nid})
            else:
                for i, step in enumerate(steps):
                    var_name = f"step_{i}"
                    variables[var_name] = {"type": "int", "low": 0, "high": max_steps}
                    if i > 0:
                        constraints.append({"type": "ordering", "before": f"step_{i-1}", "after": var_name})
            # Resource budget (plan length)
            variables["plan_length"] = {"type": "int", "low": 0, "high": self.config.max_plan_length}
            constraints.append({
                "type": "linear",
                "terms": {"plan_length": 1},
                "op": "<=",
                "rhs": self.config.max_plan_length,
            })
            objectives.append({"terms": {"step_count": -1}})
            cm = ConstraintModel(variables=variables, constraints=constraints, objectives=objectives)
            self.obs.record_latency("neuro_symbolic.bridge.forward", time.time() - start)
            self.obs.count_node("neuro_symbolic.bridge.forward", "success")
        return cm

    def backward(self, solver_result: SolverResult) -> str:
        """Generate a human-readable annotation from a solver result."""
        if solver_result.status == "sat":
            return "Symbolic verification passed: plan constraints are satisfiable."
        if solver_result.status == "unsat":
            ce = solver_result.counterexample or {}
            explanation = solver_result.explanation or "Constraints are unsatisfiable."
            return f"Symbolic verification failed: {explanation} Counter-example: {ce}"
        return f"Symbolic verification inconclusive: {solver_result.explanation}"


class SymbolicPlanner:
    """Layer 3 symbolic planning validator: translates plans to constraints and verifies with a solver."""

    def __init__(self, config: NeuroSymbolicConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self.bridge = NeuroSymbolicBridge(config, observability)

    def plan(self, state: AIOState) -> AIOState:
        """Translate plan to constraints, run solver, and store result in state."""
        start = time.time()
        with self.obs.start_span("symbolic_planner.plan", state.get("trace_id")):
            cm = self.bridge.forward(state)
            state["symbolic_constraints"] = {
                "variables": cm.variables,
                "constraints": cm.constraints,
                "objectives": cm.objectives,
            }
            result = self.backend.solve(cm, timeout_ms=self.config.symbolic_timeout_ms)
            state["symbolic_solver_result"] = {
                "status": result.status,
                "model": result.model,
                "counterexample": result.counterexample,
                "explanation": result.explanation,
            }
            if result.status == "sat":
                state["symbolic_plan_validated"] = True
                self.obs.count_node("symbolic_planner.plan", "sat")
            elif result.status == "unsat":
                state["symbolic_plan_validated"] = False
                annotation = self.bridge.backward(result)
                plan = state.get("plan", "") or ""
                state["plan"] = f"[SYMBOLIC BLOCKED] {annotation}\n{plan}"
                self.obs.count_node("symbolic_planner.plan", "unsat")
            else:
                state["symbolic_plan_validated"] = None
                self.obs.count_node("symbolic_planner.plan", "unknown")
            self.obs.record_latency("symbolic_planner.plan", time.time() - start)
        return state

    @property
    def backend(self) -> SymbolicSolverBackend:
        return self.bridge.backend


class PlanVerifier:
    """Layer 5 symbolic plan verifier: contributes a solver-based check to the formal judge ensemble."""

    def __init__(self, config: NeuroSymbolicConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self.bridge = NeuroSymbolicBridge(config, observability)

    def verify(self, state: AIOState) -> Dict[str, Any]:
        """Run symbolic verification and return a verdict dict."""
        start = time.time()
        with self.obs.start_span("plan_verifier.verify", state.get("trace_id")):
            cm = self.bridge.forward(state)
            result = self.backend.solve(cm, timeout_ms=self.config.symbolic_timeout_ms)
            verdict = {
                "satisfiable": result.status == "sat",
                "counterexample": result.counterexample,
                "explanation": result.explanation,
                "checks": [
                    {"rule": "symbolic_satisfiability", "passed": result.status == "sat"},
                ],
            }
            state["symbolic_verdict"] = verdict
            self.obs.record_latency("plan_verifier.verify", time.time() - start)
            self.obs.count_node("plan_verifier.verify", "passed" if result.status == "sat" else "failure")
        return verdict

    @property
    def backend(self) -> SymbolicSolverBackend:
        return self.bridge.backend


class NeuroSymbolicMandate:
    """Cross-cutting neuro-symbolic layer — hybrid reasoning for planning, verification, and governance.

    Combines neural (LLM) parsing with symbolic forward-chaining inference,
    knowledge-graph grounding, and formal constraint verification.  The
    mandate can be invoked as a graph node or called directly by other
    layers.

    Args:
        config: Neuro-symbolic configuration.
        observability: Shared observability layer.
    """

    def __init__(self, config: NeuroSymbolicConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self.engine = SymbolicEngine(self._load_default_rules())
        self.kg = KnowledgeGraph()
        self.formal = FormalVerifier(config)
        self._llm: Optional[Any] = None
        if config.enable_llm_parsing and LANGCHAIN_CHAT_AVAILABLE:
            self._llm = self._init_llm()

    def _load_default_rules(self) -> List[SymbolicRule]:
        rules = [
            SymbolicRule("safety_first", ["plan has safety step"], "plan is safe", weight=1.0),
            SymbolicRule("verify_before_exec", ["plan has verification step"], "plan is verified", weight=0.9),
            SymbolicRule("memory_grounded", ["plan references memory"], "plan is grounded", weight=0.8),
            SymbolicRule("unsafe_blocks_exec", ["plan is safe", "plan is verified"], "plan may execute", weight=1.0),
        ]
        if self.config.custom_rules_json:
            try:
                data = json.loads(self.config.custom_rules_json)
                for item in data:
                    rules.append(SymbolicRule(
                        name=item.get("name", "custom"),
                        premises=item.get("premises", []),
                        conclusion=item.get("conclusion", ""),
                        weight=float(item.get("weight", 1.0)),
                    ))
            except Exception as exc:
                self.obs.log(logging.WARNING, f"NeuroSymbolic: failed to load custom rules: {exc}")
        return rules

    def _init_llm(self) -> Optional[Any]:
        provider = self.config.llm_parser_provider
        if provider == "openai" and ChatOpenAI is not None:
            key = os.getenv("OPENAI_API_KEY")
            if key:
                return ChatOpenAI(
                    model=self.config.llm_parser_model,
                    temperature=self.config.llm_parser_temperature,
                    max_tokens=self.config.llm_parser_max_tokens,
                    api_key=key,
                )
            self.obs.log(logging.WARNING, "NeuroSymbolic: OPENAI_API_KEY not set")
        elif provider == "anthropic" and ChatAnthropic is not None:
            key = os.getenv("ANTHROPIC_API_KEY")
            if key:
                return ChatAnthropic(
                    model=self.config.llm_parser_model,
                    temperature=self.config.llm_parser_temperature,
                    max_tokens=self.config.llm_parser_max_tokens,
                    api_key=key,
                )
            self.obs.log(logging.WARNING, "NeuroSymbolic: ANTHROPIC_API_KEY not set")
        return None

    def _call_llm(self, prompt: str, span_name: str) -> str:
        if self._llm is None:
            raise RuntimeError("LLM parser not available")
        start = time.time()
        with self.obs.start_span(span_name):
            try:
                response = self._llm.invoke(prompt)
                text = str(response.content if hasattr(response, "content") else response)
                self.obs.record_latency(span_name, time.time() - start)
                self.obs.count_node(span_name, "success")
                return text
            except Exception as exc:
                self.obs.record_latency(span_name, time.time() - start)
                self.obs.count_node(span_name, "failure")
                self.obs.log(logging.WARNING, f"NeuroSymbolic {span_name} failed: {exc}")
                raise

    def parse_to_logic(self, state: AIOState) -> AIOState:
        """Convert the natural-language plan into a symbolic representation.

        Uses an LLM when available and ``enable_llm_parsing`` is *True*;
        otherwise falls back to a lightweight heuristic parser.
        """
        start = time.time()
        with self.obs.start_span("neuro_symbolic.parse", state.get("trace_id")):
            plan = state.get("plan", "") or ""
            if self._llm is not None and self.config.enable_llm_parsing:
                try:
                    sym = self._llm_parse(plan)
                except Exception as exc:
                    self.obs.log(logging.WARNING, f"LLM parse failed, falling back to heuristic: {exc}")
                    self.obs.count_node("neuro_symbolic.parse", "fallback")
                    sym = self._heuristic_parse(plan)
            else:
                sym = self._heuristic_parse(plan)
            state["neuro_symbolic_plan"] = sym
            self.obs.record_latency("neuro_symbolic.parse", time.time() - start)
            self.obs.count_node("neuro_symbolic.parse", "success")
        return state

    def _heuristic_parse(self, plan: str) -> Dict[str, Any]:
        steps = [s.strip() for s in re.split(r"\d+\)", plan) if s.strip()]
        return {
            "goal": "general",
            "steps": steps,
            "entities": [],
            "relations": [],
        }

    def _llm_parse(self, plan: str) -> Dict[str, Any]:
        prompt = (
            "Convert the following plan into a structured symbolic representation.\n"
            "Return ONLY valid JSON with keys: goal (string), steps (list of strings), "
            "entities (list of {id, type}), relations (list of {source, relation, target}).\n\n"
            f"Plan: {plan}\n"
        )
        text = self._call_llm(prompt, "neuro_symbolic.llm_parse")
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        try:
            parsed = json.loads(cleaned)
        except Exception:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}
        parsed.setdefault("goal", "general")
        parsed.setdefault("steps", [])
        parsed.setdefault("entities", [])
        parsed.setdefault("relations", [])
        return parsed

    def infer(self, state: AIOState) -> AIOState:
        """Run symbolic forward-chaining inference over the parsed plan.

        Populates ``neuro_symbolic_inference`` with derived facts and
        provenance.
        """
        start = time.time()
        with self.obs.start_span("neuro_symbolic.infer", state.get("trace_id")):
            sym = state.get("neuro_symbolic_plan", {}) or {}
            self.engine.reset()
            # Seed facts from symbolic plan
            for step in sym.get("steps", []):
                self.engine.add_fact(step)
            if sym.get("goal"):
                self.engine.add_fact(f"goal is {sym['goal']}")
            # Seed from memory if available
            for mem in state.get("working_memory", []) or []:
                content = mem.get("content")
                if content:
                    self.engine.add_fact(f"memory: {content}")
            # Seed from safety violations
            if state.get("safety_violations"):
                self.engine.add_fact("plan has safety step")
            if state.get("verification_result"):
                self.engine.add_fact("plan has verification step")
            result = self.engine.infer(max_depth=self.config.max_inference_depth)
            state["neuro_symbolic_inference"] = result
            self.obs.record_latency("neuro_symbolic.infer", time.time() - start)
            self.obs.count_node("neuro_symbolic.infer", "success" if result["derived"] else "none")
        return state

    def ground_knowledge(self, state: AIOState) -> AIOState:
        """Ground symbolic entities in the knowledge graph.

        Populates ``neuro_symbolic_grounding`` with KG queries and
        relevance scores.
        """
        start = time.time()
        with self.obs.start_span("neuro_symbolic.ground", state.get("trace_id")):
            sym = state.get("neuro_symbolic_plan", {}) or {}
            for ent in sym.get("entities", []):
                self.kg.add_entity(
                    ent.get("id", "unknown"),
                    ent.get("type", "unknown"),
                    ent.get("properties", {}),
                )
            for rel in sym.get("relations", []):
                self.kg.add_relation(
                    rel.get("source", ""),
                    rel.get("relation", ""),
                    rel.get("target", ""),
                    rel.get("confidence", 1.0),
                )
            groundings = []
            for ent in sym.get("entities", []):
                eid = ent.get("id", "")
                related = self.kg.query(eid)
                if related:
                    groundings.append({"entity": eid, "related": related})
            state["neuro_symbolic_grounding"] = groundings
            self.obs.record_latency("neuro_symbolic.ground", time.time() - start)
            self.obs.count_node("neuro_symbolic.ground", "success" if groundings else "none")
        return state

    def verify_constraints(self, state: AIOState) -> AIOState:
        """Run formal constraint verification and produce a verdict.

        Writes ``neuro_symbolic_verdict`` and ``neuro_symbolic_confidence``.
        """
        start = time.time()
        with self.obs.start_span("neuro_symbolic.verify", state.get("trace_id")):
            plan = state.get("plan", "") or ""
            sym = state.get("neuro_symbolic_plan", {}) or {}
            verdict = self.formal.verify(plan, sym)
            # Blend symbolic inference confidence into the verdict
            inference = state.get("neuro_symbolic_inference") or {}
            derived = inference.get("derived", [])
            avg_weight = sum(d.get("weight", 1.0) for d in derived) / max(len(derived), 1)
            confidence = avg_weight if verdict["passed"] else avg_weight * 0.5
            state["neuro_symbolic_verdict"] = verdict
            state["neuro_symbolic_confidence"] = round(confidence, 4)
            self.obs.record_latency("neuro_symbolic.verify", time.time() - start)
            self.obs.count_node("neuro_symbolic.verify", "passed" if verdict["passed"] else "failed")
        return state

    def synthesize(self, state: AIOState) -> AIOState:
        """Blend neuro-symbolic results back into the plan and verification.

        Augments the existing ``verification_result`` with symbolic
        findings and, when the formal verdict fails, enriches the plan
        with mitigation annotations.
        """
        start = time.time()
        with self.obs.start_span("neuro_symbolic.synthesize", state.get("trace_id")):
            verdict = state.get("neuro_symbolic_verdict", {})
            inference = state.get("neuro_symbolic_inference", {})
            vresult = state.setdefault("verification_result", {})
            vresult["neuro_symbolic"] = {
                "verdict": verdict,
                "inference": inference,
            }
            if not verdict.get("passed", True):
                plan = state.get("plan", "") or ""
                mitigations = [c["rule"] for c in verdict.get("checks", []) if not c.get("passed")]
                annotated = f"[NEURO-SYMBOLIC MITIGATION] Issues: {', '.join(mitigations)}\n{plan}"
                state["plan"] = annotated
            self.obs.record_latency("neuro_symbolic.synthesize", time.time() - start)
            self.obs.count_node("neuro_symbolic.synthesize", "success")
        return state
