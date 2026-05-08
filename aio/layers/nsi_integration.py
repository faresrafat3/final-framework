from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from ..config.models import NSIIntegrationConfig
from .observability import ObservabilityLayer
from ..state import AIOState


class NSIIntegration:
    """Neuro-Symbolic Integration layer for Horn-clause lifting.

    Converts natural-language assertions and plan steps into Horn clauses,
    runs forward/backward inference, and lifts results back into the
    neuro-symbolic plan representation.
    """

    def __init__(self, config: NSIIntegrationConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._clauses: List[Dict[str, Any]] = []
        self._facts: set[str] = set()

    def _normalize_atom(self, text: str) -> str:
        """Normalize a natural-language string into a predicate atom."""
        lowered = text.lower().strip()
        # Remove trailing punctuation
        lowered = lowered.rstrip(".")
        # Replace spaces with underscores and limit length
        atom = lowered.replace(" ", "_")[:64]
        return atom

    def lift_to_horn(self, state: AIOState) -> AIOState:
        """Extract assertions from state and lift them to Horn clauses.

        Populates ``nsi_horn_clauses`` in state.
        """
        start = time.time()
        with self.obs.start_span("nsi.lift", state.get("trace_id")):
            clauses: List[Dict[str, Any]] = []
            sym_plan = state.get("neuro_symbolic_plan", {}) or {}

            # Lift plan steps as facts
            for step in sym_plan.get("steps", []):
                atom = self._normalize_atom(step)
                if atom:
                    clauses.append({
                        "head": atom,
                        "body": [],
                        "type": "fact",
                        "source": "plan_step",
                    })

            # Lift relations as Horn rules (source -> target)
            for rel in sym_plan.get("relations", []):
                src = self._normalize_atom(rel.get("source", ""))
                tgt = self._normalize_atom(rel.get("target", ""))
                if src and tgt:
                    clauses.append({
                        "head": tgt,
                        "body": [src],
                        "type": "rule",
                        "source": "relation",
                    })

            # Lift safety violations as negated facts (integrity constraints)
            for v in state.get("safety_violations", []) or []:
                cat = self._normalize_atom(v.get("category", "violation"))
                clauses.append({
                    "head": f"unsafe_{cat}",
                    "body": [],
                    "type": "fact",
                    "source": "safety_violation",
                })

            # Lift verification result as a rule
            vresult = state.get("verification_result", {})
            if vresult.get("passed"):
                clauses.append({
                    "head": "plan_verified",
                    "body": [],
                    "type": "fact",
                    "source": "verification",
                })
            else:
                clauses.append({
                    "head": "plan_not_verified",
                    "body": [],
                    "type": "fact",
                    "source": "verification",
                })

            self._clauses = clauses
            state["nsi_horn_clauses"] = clauses
            self.obs.record_latency("nsi.lift", time.time() - start)
            self.obs.count_node("nsi.lift", "success" if clauses else "none")
        return state

    def forward_infer(self, state: AIOState) -> AIOState:
        """Run forward chaining over the lifted Horn clauses.

        Populates ``nsi_inferred_facts``.
        """
        start = time.time()
        with self.obs.start_span("nsi.infer", state.get("trace_id")):
            facts: set[str] = set()
            for c in self._clauses:
                if c["type"] == "fact":
                    facts.add(c["head"])

            changed = True
            derived: List[Dict[str, Any]] = []
            iterations = 0
            while changed and iterations < self.config.max_inference_iterations:
                changed = False
                iterations += 1
                for c in self._clauses:
                    if c["type"] == "rule":
                        if all(b in facts for b in c["body"]) and c["head"] not in facts:
                            facts.add(c["head"])
                            derived.append({"rule": c, "head": c["head"]})
                            changed = True

            self._facts = facts
            state["nsi_inferred_facts"] = sorted(facts)
            state["nsi_derived_rules"] = derived
            self.obs.record_latency("nsi.infer", time.time() - start)
            self.obs.count_node("nsi.infer", "success" if derived else "none")
        return state

    def lift_back(self, state: AIOState) -> AIOState:
        """Lift inferred facts back into the neuro-symbolic plan structure.

        Updates ``neuro_symbolic_plan`` with enriched entities and relations.
        """
        start = time.time()
        with self.obs.start_span("nsi.lift_back", state.get("trace_id")):
            sym_plan = state.setdefault("neuro_symbolic_plan", {})
            sym_plan.setdefault("entities", [])
            sym_plan.setdefault("relations", [])

            for fact in sorted(self._facts):
                if not any(e.get("id") == fact for e in sym_plan["entities"]):
                    sym_plan["entities"].append({
                        "id": fact,
                        "type": "inferred_fact",
                        "properties": {"source": "nsi"},
                    })

            # Create relations from derived rules
            for d in state.get("nsi_derived_rules", []):
                rule = d["rule"]
                for body_atom in rule.get("body", []):
                    sym_plan["relations"].append({
                        "source": body_atom,
                        "relation": "implies",
                        "target": rule["head"],
                        "confidence": 1.0,
                    })

            state["neuro_symbolic_plan"] = sym_plan
            self.obs.record_latency("nsi.lift_back", time.time() - start)
            self.obs.count_node("nsi.lift_back", "success")
        return state

    def run(self, state: AIOState) -> AIOState:
        """Execute the full NSI pipeline: lift -> infer -> lift_back."""
        state = self.lift_to_horn(state)
        state = self.forward_infer(state)
        state = self.lift_back(state)
        return state
