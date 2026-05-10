from __future__ import annotations

import hashlib
import logging
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from ..config.models import MemoryConfig
from ..memory.embeddings import EmbeddingEngineFactory
from ..memory.lifecycle import MemoryLifecycleEngine
from .observability import ObservabilityLayer
from ..state import AIOState
from .memory_backends import (
    BaseMemoryBackend,
    InMemoryBackend,
    RedisBackend,
    PostgresBackend,
    HybridBackend,
)

logger = logging.getLogger(__name__)


class MemoryBridge:
    """Layer 2 — Dual-memory bridge implementing encode-verify-store-consolidate-retrieve-forget.

    Args:
        config: Layer 2 configuration (backend, embeddings, TTLs).
        observability: Shared observability layer for spans and metrics.
    """

    def __init__(self, config: MemoryConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._backend = self._create_backend(config)
        self._episodic: Dict[str, Dict[str, Any]] = self._backend.episodic
        self._long_term: Dict[str, Dict[str, Any]] = self._backend.long_term
        self._keyword_index: Dict[str, List[str]] = self._backend.keyword_index
        self._embedding_engine = EmbeddingEngineFactory.create(config)
        self._lifecycle = MemoryLifecycleEngine(config, observability)

    def _create_backend(self, config: MemoryConfig) -> BaseMemoryBackend:
        backend_type = config.backend_type.lower()
        if backend_type == "redis":
            try:
                return RedisBackend(config.redis_url)
            except Exception as exc:  # pragma: no cover
                logger.warning("RedisBackend init failed: %s. Falling back to InMemoryBackend.", exc)
                return InMemoryBackend()
        if backend_type == "postgres":
            try:
                return PostgresBackend(
                    config.postgres_url,
                    vector_dimension=config.vector_dimension,
                    pgvector_enable=config.pgvector_enable,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("PostgresBackend init failed: %s. Falling back to InMemoryBackend.", exc)
                return InMemoryBackend()
        if backend_type == "hybrid":
            try:
                return HybridBackend(config.redis_url, config.postgres_url)
            except Exception as exc:  # pragma: no cover
                logger.warning("HybridBackend init failed: %s. Falling back to InMemoryBackend.", exc)
                return InMemoryBackend()
        if backend_type != "memory":
            logger.warning("Unknown MEMORY_BACKEND_TYPE '%s'. Falling back to InMemoryBackend.", config.backend_type)
        return InMemoryBackend()

    def close(self) -> None:
        self._backend.close()

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _mia_score(self, entry: Dict[str, Any]) -> float:
        """Memory Importance Assessment: composite score [0,1]."""
        base = 0.5
        if entry.get("role") == "user":
            base += 0.1
        if "error" in str(entry.get("content", "")).lower():
            base += 0.2
        if entry.get("verification_passed"):
            base += 0.1
        recency = max(0.0, 1.0 - (time.time() - entry.get("timestamp", time.time())) / 3600)
        return min(1.0, base + recency * 0.1)

    def _embed(self, content: str) -> List[float]:
        """Return real or pseudo embedding depending on config and availability."""
        return self._embedding_engine.embed(content)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        return max(0.0, min(1.0, dot))

    def _index_keywords(self, entry_id: str, content: str) -> None:
        words = set(re.findall(r"\b\w{3,}\b", content.lower()))
        for w in words:
            self._keyword_index.setdefault(w, []).append(entry_id)

    def encode(self, state: AIOState) -> AIOState:
        """Hash and embed every message in ``context_window``, then store episodically.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state (``working_memory`` and ``long_term_memory`` are updated indirectly).
        """
        start = time.time()
        with self.obs.start_span("memory.encode", state.get("trace_id")):
            window = state.get("context_window", [])
            for msg in window:
                content = str(msg.get("content", ""))
                eid = self._hash(content)
                if eid in self._episodic:
                    continue
                embedding = self._embed(content)
                entry = {
                    "id": eid,
                    "role": msg.get("role", "unknown"),
                    "content": content,
                    "turn": msg.get("turn", 0),
                    "timestamp": time.time(),
                    "embedding": embedding,
                    "verification_passed": False,
                }
                entry["importance"] = self._mia_score(entry)
                self._episodic[eid] = entry
                self._index_keywords(eid, content)
            self.obs.record_latency("memory.encode", time.time() - start)
            self.obs.count_node("memory.encode", "success")
        self._backend.sync()
        return state

    def verify(self, state: AIOState) -> AIOState:
        """Deduplicate episodic entries and mark them as verified.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with cleaned episodic store.
        """
        start = time.time()
        with self.obs.start_span("memory.verify", state.get("trace_id")):
            seen: set = set()
            for eid, entry in list(self._episodic.items()):
                content = entry["content"]
                if content in seen:
                    del self._episodic[eid]
                    continue
                seen.add(content)
                if not content or len(content) > 10000:
                    entry["verification_passed"] = False
                else:
                    entry["verification_passed"] = True
            self.obs.record_latency("memory.verify", time.time() - start)
            self.obs.count_node("memory.verify", "success")
        self._backend.sync()
        return state

    def store(self, state: AIOState) -> AIOState:
        """No-op persistence hook (backend sync happens in encode/verify/consolidate).

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Unmodified state.
        """
        start = time.time()
        with self.obs.start_span("memory.store", state.get("trace_id")):
            self.obs.record_latency("memory.store", time.time() - start)
            self.obs.count_node("memory.store", "success")
        return state

    def consolidate(self, state: AIOState) -> AIOState:
        """Promote aged, verified episodic entries to long-term memory.

        When ``enable_llm_consolidation`` is *True* and an LLM is available,
        episodic batches are summarized into a semantic long-term entry.
        Otherwise the heuristic fallback (top-important snippets) is used.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``long_term_memory`` updated.
        """
        start = time.time()
        with self.obs.start_span("memory.consolidate", state.get("trace_id")):
            batch: List[Dict[str, Any]] = []
            cutoff = time.time() - self.config.epiphany_ttl_seconds
            for eid, entry in list(self._episodic.items()):
                if entry["timestamp"] < cutoff and entry.get("verification_passed"):
                    batch.append(entry)
                if len(batch) >= self.config.consolidation_batch_size:
                    break

            if batch:
                new_lt_entries = self._lifecycle.run_consolidation(
                    batch, embed_fn=self._embed, hash_fn=self._hash
                )
                for lt_entry in new_lt_entries:
                    lt_eid = lt_entry["id"]
                    self._long_term[lt_eid] = lt_entry
                    self._index_keywords(lt_eid, lt_entry.get("content", ""))
                # Remove source episodic entries
                for entry in batch:
                    eid = entry["id"]
                    if eid in self._episodic:
                        del self._episodic[eid]

            state["long_term_memory"] = list(self._long_term.values())
            self.obs.record_latency("memory.consolidate", time.time() - start)
            self.obs.count_node("memory.consolidate", "success")
        self._backend.sync()
        return state

    def _bump_access_count(self, entry_id: str) -> None:
        """Increment the access counter for *entry_id* in episodic or long_term."""
        for store in (self._episodic, self._long_term):
            if entry_id in store:
                store[entry_id]["access_count"] = store[entry_id].get("access_count", 0) + 1

    def retrieve(self, state: AIOState) -> AIOState:
        """Hybrid keyword + vector search over episodic and long-term stores.

        Retrieved entries have their ``access_count`` incremented so the
        adaptive forgetting curve preserves frequently-accessed memories.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``working_memory`` and ``memory_confidence``.
        """
        start = time.time()
        with self.obs.start_span("memory.retrieve", state.get("trace_id")):
            query = state.get("raw_input", "")
            q_embed = self._embed(query)
            q_words = set(re.findall(r"\b\w{3,}\b", query.lower()))

            # Delegate to PostgresBackend hybrid_search when pgvector is active
            if (
                isinstance(self._backend, PostgresBackend)
                and getattr(self._backend, "_pgvector_active", False)
            ):
                keywords = list(q_words)
                top_k = self._backend.hybrid_search(
                    query_embedding=q_embed,
                    keywords=keywords,
                    top_k=self.config.retrieval_top_k,
                )
                pool = {**self._long_term, **self._episodic}
                retrieved = []
                for eid, score in top_k:
                    entry = pool.get(eid)
                    if entry:
                        self._bump_access_count(eid)
                        retrieved.append(entry)
                confidence = top_k[0][1] if top_k else 0.0
                state["working_memory"] = retrieved
                state["memory_confidence"] = round(confidence, 4)
                self.obs.record_latency("memory.retrieve", time.time() - start)
                self.obs.count_node("memory.retrieve", "success")
                return state

            candidate_ids: set = set()
            for w in q_words:
                candidate_ids.update(self._keyword_index.get(w, []))
            pool = {**self._long_term, **self._episodic}
            if not candidate_ids:
                candidate_ids = set(pool.keys())

            scored: List[Tuple[str, float]] = []
            for eid in candidate_ids:
                entry = pool.get(eid)
                if not entry:
                    continue
                vec_sim = self._cosine_similarity(q_embed, entry.get("embedding", q_embed))
                kw_boost = 0.1 if any(w in entry.get("content", "").lower() for w in q_words) else 0.0
                importance = entry.get("importance", 0.5)
                recency = max(0.0, 1.0 - (time.time() - entry.get("timestamp", time.time())) / 3600)
                score = vec_sim * 0.5 + importance * 0.25 + recency * 0.15 + kw_boost
                scored.append((eid, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_k = scored[: self.config.retrieval_top_k]
            retrieved = []
            for eid, _ in top_k:
                entry = pool.get(eid)
                if entry:
                    self._bump_access_count(eid)
                    retrieved.append(entry)
            confidence = top_k[0][1] if top_k else 0.0
            state["working_memory"] = retrieved
            state["memory_confidence"] = round(confidence, 4)
            self.obs.record_latency("memory.retrieve", time.time() - start)
            self.obs.count_node("memory.retrieve", "success")
        return state

    def forget(self, state: AIOState) -> AIOState:
        """Purge old, unimportant entries from both memory stores.

        Uses an adaptive Ebbinghaus forgetting curve where retention is
        modulated by importance and access count.  Higher-importance and
        frequently-accessed memories decay more slowly.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with cleaned stores.
        """
        start = time.time()
        with self.obs.start_span("memory.forget", state.get("trace_id")):
            now = time.time()
            for store in (self._episodic, self._long_term):
                to_purge = self._lifecycle.run_forget(store, now)
                for eid in to_purge:
                    if eid in store:
                        del store[eid]
                    for lst in self._keyword_index.values():
                        if eid in lst:
                            lst.remove(eid)
            self.obs.record_latency("memory.forget", time.time() - start)
            self.obs.count_node("memory.forget", "success")
        self._backend.sync()
        return state
