from __future__ import annotations

import hashlib
import random
import time
from typing import Any, Dict, List, Optional

from ..config.models import CuriosityConfig
from .observability import ObservabilityLayer
from ..state import AIOState


class CuriosityEngine:
    """Layer 4 — Proactive curiosity: intrinsic reward, active seeking, serendipity, counterfactuals, umwelt,
    latent space exploration, and active information seeking.

    Args:
        config: Layer 4 configuration (novelty threshold, reward weights).
        observability: Shared observability layer for spans and metrics.
    """

    def __init__(self, config: CuriosityConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._visited_states: set = set()
        self._latent_vectors: List[List[float]] = []

    def intrinsic_reward(self, state: AIOState) -> AIOState:
        """Compute intrinsic reward for the current plan based on novelty.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``curiosity_score`` and ``novelty_map`` updated.
        """
        start = time.time()
        with self.obs.start_span("curiosity.intrinsic_reward", state.get("trace_id")):
            plan = state.get("plan", "")
            state_hash = hashlib.sha256(str(plan).encode()).hexdigest()[:16]
            novelty = 1.0 if state_hash not in self._visited_states else 0.1
            self._visited_states.add(state_hash)
            score = novelty * self.config.intrinsic_reward_weight
            state["curiosity_score"] = round(score, 4)
            state.setdefault("novelty_map", {})[state_hash] = round(novelty, 4)
            self.obs.record_latency("curiosity.intrinsic_reward", time.time() - start)
            self.obs.count_node("curiosity.intrinsic_reward", "success")
        return state

    def active_seek(self, state: AIOState) -> AIOState:
        """Identify information gaps and formulate questions to close them.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``information_gaps``.
        """
        start = time.time()
        with self.obs.start_span("curiosity.active_seek", state.get("trace_id")):
            gaps = []
            if not state.get("working_memory"):
                gaps.append("No relevant working memory; need to retrieve or encode more context.")
            if state.get("memory_confidence", 0.0) < 0.5:
                gaps.append("Low memory confidence; seek additional facts.")
            state["information_gaps"] = gaps
            self.obs.record_latency("curiosity.active_seek", time.time() - start)
            self.obs.count_node("curiosity.active_seek", "success")
        return state

    def serendipity(self, state: AIOState) -> AIOState:
        """Detect unexpected patterns that may represent useful opportunities.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``metrics["serendipity_insight"]``.
        """
        start = time.time()
        with self.obs.start_span("curiosity.serendipity", state.get("trace_id")):
            plan = state.get("plan", "")
            insight = None
            if "error" in str(plan).lower():
                insight = "Serendipity: Plan mentions error handling—opportunity to improve robustness."
            state.setdefault("metrics", {})["serendipity_insight"] = insight
            self.obs.record_latency("curiosity.serendipity", time.time() - start)
            self.obs.count_node("curiosity.serendipity", "success")
        return state

    def counterfactual(self, state: AIOState) -> AIOState:
        """Explore counterfactual what-if scenarios with structured generation.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``metrics["counterfactuals"]``.
        """
        start = time.time()
        with self.obs.start_span("curiosity.counterfactual", state.get("trace_id")):
            plan = state.get("plan", "")
            alternatives: List[Dict[str, Any]] = [
                {
                    "hypothesis": "skip_verification",
                    "description": f"What if we skipped verification? Plan: {plan}",
                    "expected_risk": "high",
                },
                {
                    "hypothesis": "different_tool",
                    "description": f"What if we used a different tool? Plan: {plan}",
                    "expected_risk": "medium",
                },
                {
                    "hypothesis": "no_sandbox",
                    "description": f"What if we disabled the sandbox? Plan: {plan}",
                    "expected_risk": "critical",
                },
            ]
            state.setdefault("metrics", {})["counterfactuals"] = alternatives
            self.obs.record_latency("curiosity.counterfactual", time.time() - start)
            self.obs.count_node("curiosity.counterfactual", "success")
        return state

    def umwelt_constraints(self, state: AIOState) -> AIOState:
        """Apply Umwelt Engineering constraints to the agent's perceptual boundary.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``metrics["umwelt_constraints"]``.
        """
        start = time.time()
        with self.obs.start_span("curiosity.umwelt", state.get("trace_id")):
            constraints = self.config.umwelt_constraints or [
                "No network access beyond localhost",
                "Read-only filesystem for sandbox",
                "Max 512MB memory per tool call",
            ]
            state.setdefault("metrics", {})["umwelt_constraints"] = constraints
            self.obs.record_latency("curiosity.umwelt", time.time() - start)
            self.obs.count_node("curiosity.umwelt", "success")
        return state

    def latent_space_explore(self, state: AIOState) -> AIOState:
        """Explore a synthetic latent space around the current plan embedding.

        Generates perturbed vectors and stores them for downstream novelty
        computation. Populates ``metrics["latent_exploration"]``.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with latent exploration metadata.
        """
        start = time.time()
        with self.obs.start_span("curiosity.latent_explore", state.get("trace_id")):
            plan = state.get("plan", "") or ""
            # Deterministic pseudo-embedding from plan hash
            seed = int(hashlib.sha256(plan.encode()).hexdigest(), 16) % (2**31)
            rng = random.Random(seed)
            base = [rng.uniform(-1.0, 1.0) for _ in range(self.config.latent_dim)]
            neighbors: List[List[float]] = []
            for _ in range(self.config.latent_neighbors):
                noise = [rng.gauss(0, self.config.latent_noise_sigma) for _ in range(self.config.latent_dim)]
                neighbor = [round(base[i] + noise[i], 4) for i in range(self.config.latent_dim)]
                neighbors.append(neighbor)
            self._latent_vectors.append(base)
            state.setdefault("metrics", {})["latent_exploration"] = {
                "base_vector": [round(v, 4) for v in base],
                "neighbors": neighbors,
                "neighbor_count": len(neighbors),
            }
            self.obs.record_latency("curiosity.latent_explore", time.time() - start)
            self.obs.count_node("curiosity.latent_explore", "success")
        return state

    def active_information_seeking(self, state: AIOState) -> AIOState:
        """Actively generate information-seeking queries when gaps are detected.

        When memory confidence is low or working memory is empty, generates
        a list of queries that can be dispatched to retrieval or external tools.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``information_seeking_queries``.
        """
        start = time.time()
        with self.obs.start_span("curiosity.information_seeking", state.get("trace_id")):
            queries: List[str] = []
            intent = state.get("intent", "general")
            raw = state.get("raw_input", "")
            if state.get("memory_confidence", 0.0) < 0.5:
                queries.append(f"Retrieve relevant context for intent '{intent}' and query '{raw}'.")
            if not state.get("working_memory"):
                queries.append(f"Encode missing background knowledge for '{raw}'.")
            if state.get("verification_result", {}).get("passed") is False:
                queries.append("Retrieve critique guidelines to improve plan quality.")
            state["information_seeking_queries"] = queries
            self.obs.record_latency("curiosity.information_seeking", time.time() - start)
            self.obs.count_node("curiosity.information_seeking", "success" if queries else "none")
        return state
