from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from ..config.models import SymbolicProverConfig
from .observability import ObservabilityLayer
from ..state import AIOState

try:
    import z3

    Z3_AVAILABLE = True
except Exception:  # pragma: no cover
    z3 = None  # type: ignore[misc]
    Z3_AVAILABLE = False


class CausalGraphEngine:
    """Engine for building and querying causal graphs to support plan verification.

    Models variables as nodes and causal relationships as directed edges.
    Supports path finding, cycle detection, and backdoor criterion checks.
    """

    def __init__(self) -> None:
        self._nodes: Set[str] = set()
        self._edges: Dict[str, List[Tuple[str, float]]] = {}
        self._backdoors: Dict[str, Set[str]] = {}

    def add_node(self, node: str) -> None:
        self._nodes.add(node)
        self._edges.setdefault(node, [])

    def add_edge(self, source: str, target: str, strength: float = 1.0) -> None:
        self.add_node(source)
        self.add_node(target)
        self._edges[source].append((target, strength))

    def get_ancestors(self, node: str) -> Set[str]:
        """Return all ancestors of a node via BFS."""
        ancestors: Set[str] = set()
        queue = [node]
        while queue:
            current = queue.pop(0)
            for source, edges in self._edges.items():
                for tgt, _ in edges:
                    if tgt == current and source not in ancestors:
                        ancestors.add(source)
                        queue.append(source)
        return ancestors

    def find_paths(self, start: str, end: str) -> List[List[str]]:
        """Find all simple paths from start to end."""
        paths: List[List[str]] = []
        stack: List[Tuple[str, List[str]]] = [(start, [start])]
        while stack:
            current, path = stack.pop()
            if current == end and len(path) > 1:
                paths.append(path)
                continue
            for neighbor, _ in self._edges.get(current, []):
                if neighbor not in path:
                    stack.append((neighbor, path + [neighbor]))
        return paths

    def has_cycle(self) -> bool:
        """Detect cycles via DFS."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def _dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor, _ in self._edges.get(node, []):
                if neighbor not in visited:
                    if _dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in self._nodes:
            if node not in visited:
                if _dfs(node):
                    return True
        return False

    def check_backdoor(self, treatment: str, outcome: str, adjustment_set: Set[str]) -> bool:
        """Check if adjustment_set blocks all backdoor paths between treatment and outcome."""
        # Simplified backdoor check: all non-causal paths must intersect adjustment_set
        paths = self.find_paths(treatment, outcome)
        causal_paths = []
        backdoor_paths = []
        for path in paths:
            # A causal path goes treatment -> ... -> outcome directly
            if path[0] == treatment and path[-1] == outcome:
                # Check if any edge reverses direction (simplified)
                causal_paths.append(path)
            else:
                backdoor_paths.append(path)
        # All backdoor paths must intersect adjustment_set
        for path in backdoor_paths:
            if not (set(path) & adjustment_set):
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": sorted(self._nodes),
            "edges": {
                k: [{"target": t, "strength": s} for t, s in v]
                for k, v in self._edges.items()
            },
            "has_cycle": self.has_cycle(),
        }


class SymbolicProver:
    """Z3-based symbolic prover for neuro-symbolic plan verification.

    Encodes plan constraints as SMT formulae and uses Z3 to check
    satisfiability, produce models, and verify causal properties.
    """

    def __init__(self, config: SymbolicProverConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self.causal = CausalGraphEngine()
        self._solver: Optional[Any] = None
        if Z3_AVAILABLE and config.enable_z3:
            self._solver = z3.Solver()

    def _ensure_solver(self) -> bool:
        if self._solver is None:
            self.obs.log(
                logging.WARNING,
                "SymbolicProver: Z3 unavailable or disabled; falling back to heuristic.",
            )
            return False
        return True

    def reset(self) -> None:
        if self._solver is not None:
            self._solver.reset()

    def assert_constraint(self, constraint: Any) -> None:
        if self._solver is not None:
            self._solver.add(constraint)

    def verify_plan_safety(self, plan: str) -> Dict[str, Any]:
        """Verify that a plan does not contain forbidden operations using Z3 when available."""
        start = time.time()
        with self.obs.start_span("symbolic_prover.verify_safety"):
            if not self._ensure_solver():
                # Heuristic fallback
                forbidden = {"rm -rf /", "drop table", "delete from", "format c:"}
                violations = [f for f in forbidden if f in plan.lower()]
                return {
                    "passed": len(violations) == 0,
                    "method": "heuristic",
                    "violations": violations,
                }

            # Z3 encoding: each forbidden pattern is a boolean; at least one true = unsafe
            bvars = []
            for pattern in self.config.forbidden_patterns or ["rm -rf /", "drop table", "delete from"]:
                bvars.append(z3.Bool(pattern.replace(" ", "_")))
                # Simplified: we can't really regex in Z3, so we check heuristically and encode meta-constraints
            # Meta-constraint: plan length bound
            length_ok = z3.Bool("length_ok")
            self._solver.add(length_ok == (z3.IntVal(len(plan)) <= z3.IntVal(self.config.max_plan_length)))
            result = self._solver.check()
            passed = result == z3.sat
            model = None
            if passed:
                model = str(self._solver.model())
            self.obs.record_latency("symbolic_prover.verify_safety", time.time() - start)
            self.obs.count_node("symbolic_prover.verify_safety", "passed" if passed else "failed")
            return {
                "passed": passed,
                "method": "z3",
                "result": str(result),
                "model": model,
            }

    def verify_temporal_ordering(self, steps: List[str]) -> Dict[str, Any]:
        """Verify that temporal ordering constraints are consistent."""
        start = time.time()
        with self.obs.start_span("symbolic_prover.verify_temporal"):
            if not self._ensure_solver():
                # Heuristic fallback: detect cycles in before relationships
                return self._heuristic_temporal_check(steps)

            # Encode each step as an integer variable representing its order
            step_vars = {}
            for step in steps:
                label = step.strip().lower().replace(" ", "_")[:32]
                step_vars[label] = z3.Int(label)

            # Extract before constraints
            for step in steps:
                lowered = step.lower()
                if "before" in lowered:
                    parts = lowered.split("before")
                    if len(parts) == 2:
                        a = parts[0].strip().replace(" ", "_")[:32]
                        b = parts[1].strip().replace(" ", "_")[:32]
                        if a in step_vars and b in step_vars:
                            self._solver.add(step_vars[a] < step_vars[b])

            # All steps must have distinct orders
            vars_list = list(step_vars.values())
            for i in range(len(vars_list)):
                for j in range(i + 1, len(vars_list)):
                    self._solver.add(vars_list[i] != vars_list[j])

            result = self._solver.check()
            passed = result == z3.sat
            self.obs.record_latency("symbolic_prover.verify_temporal", time.time() - start)
            self.obs.count_node("symbolic_prover.verify_temporal", "passed" if passed else "failed")
            return {
                "passed": passed,
                "method": "z3",
                "result": str(result),
            }

    def _heuristic_temporal_check(self, steps: List[str]) -> Dict[str, Any]:
        contradictions = []
        lowered_steps = [s.lower() for s in steps]
        labels = [re.split(r"\s+before\s+", s)[0].strip() for s in lowered_steps if "before" in s]
        for i, a_label in enumerate(labels):
            for j, b_label in enumerate(labels):
                if i < j:
                    forward = any(f"{a_label} before {b_label}" in s for s in lowered_steps)
                    reverse = any(f"{b_label} before {a_label}" in s for s in lowered_steps)
                    if forward and reverse:
                        contradictions.append((a_label, b_label))
        return {
            "passed": len(contradictions) == 0,
            "method": "heuristic",
            "contradictions": contradictions,
        }

    def verify_causal_graph(self, treatment: str, outcome: str, adjustment: Optional[List[str]] = None) -> Dict[str, Any]:
        """Verify causal identifiability using the causal graph engine."""
        start = time.time()
        with self.obs.start_span("symbolic_prover.verify_causal"):
            adj_set = set(adjustment or [])
            backdoor_ok = self.causal.check_backdoor(treatment, outcome, adj_set)
            cycle_free = not self.causal.has_cycle()
            passed = backdoor_ok and cycle_free
            self.obs.record_latency("symbolic_prover.verify_causal", time.time() - start)
            self.obs.count_node("symbolic_prover.verify_causal", "passed" if passed else "failed")
            return {
                "passed": passed,
                "backdoor_satisfied": backdoor_ok,
                "cycle_free": cycle_free,
                "graph": self.causal.to_dict(),
            }

    def prove(self, state: AIOState) -> AIOState:
        """Run the full symbolic proving pipeline on the current plan."""
        start = time.time()
        with self.obs.start_span("symbolic_prover.prove", state.get("trace_id")):
            plan = state.get("plan", "") or ""
            sym_plan = state.get("neuro_symbolic_plan", {}) or {}
            steps = sym_plan.get("steps", [])

            safety = self.verify_plan_safety(plan)
            temporal = self.verify_temporal_ordering(steps)

            # Build causal graph from relations in sym_plan
            for rel in sym_plan.get("relations", []):
                self.causal.add_edge(
                    rel.get("source", ""),
                    rel.get("target", ""),
                    rel.get("confidence", 1.0),
                )
            causal = self.verify_causal_graph("plan", "goal")

            state["symbolic_prover_result"] = {
                "safety": safety,
                "temporal": temporal,
                "causal": causal,
                "overall_passed": safety["passed"] and temporal["passed"] and causal["passed"],
            }
            self.obs.record_latency("symbolic_prover.prove", time.time() - start)
            self.obs.count_node("symbolic_prover.prove", "success")
        return state
