# DECISION_LOG.md — Structured Decision Registry

> **Purpose**: Capture significant architectural and implementation decisions with context, consequences, and status. Future sessions should review recent entries before making changes.

---

## Format

| ID | Date | Decision | Context | Consequences | Status |
|----|------|----------|---------|--------------|--------|

---

## Decisions

| D001 | 2024-05-05 | Single-file core architecture (`aio_framework.py`) | Simplifies imports, ensures atomic consistency, reduces packaging overhead | File grew large (~2600 lines after Priority 3); modularization became necessary | Superseded by D018 |
| D002 | 2024-05-05 | Pydantic v2 for all configuration | Strong typing, validation, env var integration | Requires `pydantic>=2.0`; breaks compatibility with v1 | Active |
| D003 | 2024-05-05 | TypedDict with `total=False` for state | Allows additive fields without breaking existing code | Less strict than dataclass; typos in field names silently ignored | Active |
| D004 | 2024-05-05 | All external dependencies optional with feature flags | Enables standalone testing, reduces environment drift | Code must check flags before every external call | Active |
| D005 | 2024-05-05 | Deterministic pseudo-embeddings for memory | No external model dependency for standalone operation | Retrieval accuracy lower than real embeddings | Active |
| D006 | 2024-05-05 | Docker sandbox as default execution mode | Strong isolation, resource limits, read-only rootfs | Requires Docker socket; falls back to error gracefully | Active |
| D007 | 2024-05-06 | Implement Priority 3 (Layers 9-12) additively with zero breaking changes | Preserve all Priority 1/2 tests and graph behavior | Increased graph complexity; more conditional edges to maintain | Active |
| D008 | 2024-05-06 | Master feature flag `enable_priority_3` with per-layer sub-flags | Allows gradual rollout and individual layer disable | More config surface area; all routing functions must check flags | Active |
| D009 | 2024-05-06 | Post-finalize reflection pipeline for Layers 9, 11, 12 | Self-evolution and immune system run after output finalization | Adds latency to every turn when enabled; mitigated by lightweight operations | Active |
| D010 | 2024-05-06 | Multi-agent coordination integrates before planning as optional branch | Complex tasks get decomposed across simulated agents | Agent dispatch is simulated, not real; future work to integrate actual agents | Active |
| D011 | 2024-05-06 | Safety governance audit gate runs before verification | Adds constitutional compliance check to planning pipeline | May block valid plans if compliance is overly strict; threshold is configurable | Active |
| D012 | 2024-05-06 | Immune system quarantine copies but does not delete until heal() | Prevents data loss from false positives | Quarantine store grows until heal() runs; mitigated by TTL | Active |
| D013 | 2024-05-06 | Self-evolution auto-apply whitelists only bounded config keys | Prevents safety threshold or layer disable from automatic changes | Only `retrieval_top_k`, backoff timing, and similar tunables can auto-apply | Active |
| D014 | 2024-05-06 | No new Python dependencies for Priority 3 | Minimizes environment drift, keeps `requirements.txt` stable | Simulated multi-agent dispatch instead of real agent framework | Active |
| D015 | 2024-05-06 | Create SESSION_START.md, PROJECT_STATE.md, DECISION_LOG.md | Prevents context loss between development sessions | Three additional files to maintain; updates required after significant changes | Active |
| D016 | 2024-05-06 | Integrate `sentence-transformers` real embeddings behind `ENABLE_REAL_EMBEDDINGS` flag | Production retrieval accuracy requires real vectors; deterministic pseudo-embeddings must remain the default for standalone testing | Adds optional dependency `sentence-transformers>=2.2.0`; fallback to pseudo-embeddings when flag is off or model fails to load; dimension-agnostic cosine similarity means no downstream changes | Active |
| D017 | 2024-05-07 | Integrate optional LLM-powered planning behind `ENABLE_LLM_PLANNING` flag with optional dependency guards | Production planning quality benefits from LLM reasoning; heuristic planners must remain for standalone testing and graceful degradation | Adds `LLMPlanner` class inside single-file core; intercepts base plan generation, HiPlan decomposition, FLARE lookahead, and PPA pitfall analysis; any LLM failure (missing import, missing API key, timeout, bad JSON) logs warning and falls back to heuristic planner without crashing graph; `langchain-openai` and `langchain-anthropic` remain optional commented lines in `requirements.txt` | Active |
| D018 | 2024-05-06 | Modularize `aio_framework.py` into `aio/` package with `layers/`, `config/`, `graph/` submodules | Single-file core grew to ~2600 lines; maintainability, testability, and parallel development required separation | `aio_framework.py` becomes a backward-compatible re-export shim; all tests and imports continue to work without changes; new code lives in `aio/layers/`, `aio/config/`, `aio/graph/` | Active |
| D019 | 2024-05-06 | Pluggable persistent memory backends for `MemoryBridge` (Redis/Postgres/Hybrid behind `MEMORY_BACKEND_TYPE` flag) | In-process memory is lost on restart; production deployments need durable, shared state | Adds `BaseMemoryBackend`, `InMemoryBackend`, `RedisBackend`, `PostgresBackend`, `HybridBackend` in `aio/layers/memory_backends.py`; each backend exposes `episodic`, `long_term`, `keyword_index` dicts for backward compatibility; persistent backends sync on lifecycle hooks; graceful fallback if Redis/Postgres is unreachable | Active |
| D020 | 2024-05-06 | ImmuneLearningEngine with Z-score anomaly detection in `CognitiveImmuneSystem` behind `COGNITIVE_IMMUNE_LEARN_ENABLE` flag | Heuristic anomaly scores are static; learning from historical threat patterns improves detection accuracy and reduces false positives | Adds `ImmuneLearningEngine` in `aio/layers/immune_learning.py`; stores snapshots in PostgreSQL; computes rolling mean/std per metric; derives learned anomaly score from Z-scores with configurable threshold and window; disabled by default; gracefully degrades to heuristic-only if Postgres is unavailable | Active |

---

## Status Definitions

- **Active**: Decision is current and governs active code.
- **Superseded**: Replaced by a later decision; retained for historical context.
- **Reverted**: Decision was undone; code no longer reflects it.

---

*Last updated: Priority 4 completion*
