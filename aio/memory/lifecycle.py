"""Memory lifecycle engine — LLM-based consolidation and adaptive forgetting.

Provides :class:`LLMConsolidator` for turning episodic entries into
semantic long-term summaries, :class:`EbbinghausForgettingCurve` for
importance-modulated retention decay, and :class:`MemoryLifecycleEngine`
which orchestrates both phases.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List, Optional

from ..config.deps import LANGCHAIN_CHAT_AVAILABLE
from ..config.models import MemoryConfig
from ..layers.observability import ObservabilityLayer

logger = logging.getLogger(__name__)

if LANGCHAIN_CHAT_AVAILABLE:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic


class LLMConsolidator:
    """LLM-powered episodic-to-long-term consolidation.

    When enabled, batches of verified episodic entries are passed to an
    LLM which produces a compact semantic summary.  The summary is stored
    as a new long-term entry with a fresh embedding and boosted importance.

    Falls back gracefully to heuristic consolidation (concatenation) when
    the LLM is unavailable or the call fails.
    """

    def __init__(self, config: MemoryConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._model: Optional[Any] = None

    def _get_chat_model(self) -> Optional[Any]:
        if not LANGCHAIN_CHAT_AVAILABLE:
            return None
        if self._model is not None:
            return self._model
        provider = self.config.llm_consolidation_provider
        if provider == "openai":
            try:
                key = __import__("os", fromlist=["getenv"]).getenv("OPENAI_API_KEY")
                if not key:
                    self.obs.log(logging.WARNING, "LLMConsolidator: OPENAI_API_KEY not set")
                    return None
                self._model = ChatOpenAI(
                    model=self.config.llm_consolidation_model,
                    temperature=0.2,
                    max_tokens=512,
                    api_key=key,
                )
                return self._model
            except Exception as exc:  # pragma: no cover
                self.obs.log(logging.WARNING, f"LLMConsolidator: Failed to init OpenAI model: {exc}")
                return None
        if provider == "anthropic":
            try:
                key = __import__("os", fromlist=["getenv"]).getenv("ANTHROPIC_API_KEY")
                if not key:
                    self.obs.log(logging.WARNING, "LLMConsolidator: ANTHROPIC_API_KEY not set")
                    return None
                self._model = ChatAnthropic(
                    model=self.config.llm_consolidation_model,
                    temperature=0.2,
                    max_tokens=512,
                    api_key=key,
                )
                return self._model
            except Exception as exc:  # pragma: no cover
                self.obs.log(logging.WARNING, f"LLMConsolidator: Failed to init Anthropic model: {exc}")
                return None
        return None

    def _call_llm(self, prompt: str) -> Optional[str]:
        model = self._get_chat_model()
        if model is None:
            return None
        start = time.time()
        with self.obs.start_span("memory.lifecycle.llm_consolidate"):
            try:
                response = model.invoke(prompt)
                text = str(response.content if hasattr(response, "content") else response)
                self.obs.record_latency("memory.lifecycle.llm_consolidate", time.time() - start)
                self.obs.count_node("memory.lifecycle.llm_consolidate", "success")
                return text.strip()
            except Exception as exc:
                self.obs.record_latency("memory.lifecycle.llm_consolidate", time.time() - start)
                self.obs.count_node("memory.lifecycle.llm_consolidate", "failure")
                self.obs.log(logging.WARNING, f"LLMConsolidator call failed: {exc}")
                return None

    def consolidate(self, entries: List[Dict[str, Any]]) -> Optional[str]:
        """Return a semantic summary of *entries*, or *None* if the LLM is unavailable.

        Args:
            entries: List of verified episodic memory entries.

        Returns:
            A concise summary string, or *None* to signal fallback.
        """
        if not entries:
            return None
        if not self.config.enable_llm_consolidation:
            return None

        snippets = []
        for i, e in enumerate(entries[: self.config.consolidation_batch_size]):
            role = e.get("role", "unknown")
            content = str(e.get("content", ""))[:300]
            snippets.append(f"{i+1}. [{role}] {content}")

        prompt = (
            "You are a memory consolidation assistant. Given the following episodic memory snippets, "
            "produce a single concise paragraph (max 3 sentences) that captures the key facts and themes. "
            "Return only the summary with no extra commentary.\n\n"
            + "\n".join(snippets)
        )
        return self._call_llm(prompt)

    def heuristic_consolidate(self, entries: List[Dict[str, Any]]) -> str:
        """Fallback heuristic: join the most important snippets.

        Args:
            entries: List of verified episodic memory entries.

        Returns:
            A concatenated summary string.
        """
        if not entries:
            return ""
        # Sort by importance descending and take top few
        sorted_entries = sorted(entries, key=lambda e: e.get("importance", 0.5), reverse=True)
        top = sorted_entries[: self.config.consolidation_batch_size]
        parts = [str(e.get("content", ""))[:200] for e in top]
        return " | ".join(parts)


class EbbinghausForgettingCurve:
    """Adaptive forgetting curve with importance-based retention modulation.

    The retention probability at time *t* follows a modified Ebbinghaus
    exponential decay where the decay constant is scaled inversely by
    importance and access count::

        retention(t) = base ^ (t / (half_life * importance_boost))

    Higher-importance items and frequently-accessed items decay more slowly.
    """

    def __init__(self, config: MemoryConfig) -> None:
        self.config = config

    def _half_life(self, entry: Dict[str, Any]) -> float:
        """Compute the effective half-life (seconds) for *entry*.

        Base half-life is ``forget_ttl_seconds``.  It is multiplied by
        ``importance * access_count`` so important, frequently-accessed
        memories survive longer.
        """
        base = float(self.config.forget_ttl_seconds)
        importance = max(0.01, min(1.0, entry.get("importance", 0.5)))
        access_count = max(1, entry.get("access_count", 1))
        boost = importance * math.log1p(access_count)
        return base * max(0.5, boost)

    def retention(self, entry: Dict[str, Any], now: Optional[float] = None) -> float:
        """Return the retention probability [0, 1] for *entry* at time *now*.

        Args:
            entry: Memory entry with ``timestamp`` and optional ``importance``,
                ``access_count``.
            now: Reference time (default ``time.time()``).

        Returns:
            Retention probability.  Values below ``importance_threshold``
            signal the entry is eligible for purging.
        """
        if now is None:
            now = time.time()
        age = now - entry.get("timestamp", now)
        if age <= 0:
            return 1.0
        half_life = self._half_life(entry)
        if half_life <= 0:
            return 0.0
        return self.config.forgetting_curve_base ** (age / half_life)

    def should_forget(self, entry: Dict[str, Any], now: Optional[float] = None) -> bool:
        """Return *True* if *entry* should be purged.

        Purging occurs when retention drops below ``importance_threshold``
        AND the entry age exceeds ``forget_ttl_seconds``.
        """
        if now is None:
            now = time.time()
        age = now - entry.get("timestamp", now)
        if age < self.config.forget_ttl_seconds:
            return False
        return self.retention(entry, now) < self.config.importance_threshold


class MemoryLifecycleEngine:
    """Orchestrates LLM consolidation and adaptive forgetting.

    This engine is invoked by :class:`aio.layers.memory.MemoryBridge` during
    the ``consolidate`` and ``forget`` lifecycle phases.
    """

    def __init__(self, config: MemoryConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self.consolidator = LLMConsolidator(config, observability)
        self.forgetting = EbbinghausForgettingCurve(config)

    def run_consolidation(
        self,
        episodic_entries: List[Dict[str, Any]],
        embed_fn: Any,
        hash_fn: Any,
    ) -> List[Dict[str, Any]]:
        """Process a batch of episodic entries and return new long-term entries.

        When LLM consolidation is enabled and available, a semantic summary is
        generated and stored as a single long-term entry.  Otherwise, the
        heuristic fallback (top-important snippets) is used.

        Args:
            episodic_entries: Verified episodic entries ready for consolidation.
            embed_fn: Callable ``(str) -> List[float]`` for generating embeddings.
            hash_fn: Callable ``(str) -> str`` for generating entry IDs.

        Returns:
            List of new long-term memory entries to be added.
        """
        if not episodic_entries:
            return []

        start = time.time()
        with self.obs.start_span("memory.lifecycle.consolidate"):
            summary = self.consolidator.consolidate(episodic_entries)
            if summary is None:
                summary = self.consolidator.heuristic_consolidate(episodic_entries)
                llm_used = False
            else:
                llm_used = True

            eid = hash_fn(summary)
            embedding = embed_fn(summary)
            # Boost importance for consolidated memories
            avg_importance = sum(e.get("importance", 0.5) for e in episodic_entries) / len(episodic_entries)
            consolidated_entry: Dict[str, Any] = {
                "id": eid,
                "role": "system",
                "content": summary,
                "timestamp": time.time(),
                "embedding": embedding,
                "importance": min(1.0, avg_importance + 0.15),
                "verification_passed": True,
                "llm_consolidated": llm_used,
                "source_entry_ids": [e.get("id") for e in episodic_entries],
                "access_count": 1,
            }
            self.obs.record_latency("memory.lifecycle.consolidate", time.time() - start)
            self.obs.count_node("memory.lifecycle.consolidate", "success")
        return [consolidated_entry]

    def run_forget(
        self,
        store: Dict[str, Dict[str, Any]],
        now: Optional[float] = None,
    ) -> List[str]:
        """Evaluate every entry in *store* and return IDs that should be purged.

        Args:
            store: Either ``episodic`` or ``long_term`` dictionary.
            now: Reference time (default ``time.time()``).

        Returns:
            List of entry IDs to delete.
        """
        if now is None:
            now = time.time()
        to_purge: List[str] = []
        for eid, entry in store.items():
            if self.forgetting.should_forget(entry, now):
                to_purge.append(eid)
        return to_purge
