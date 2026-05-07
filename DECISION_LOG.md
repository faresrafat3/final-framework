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
| D021 | 2024-05-06 | LangGraph multi-agent backend abstraction | Simulated dispatch was sufficient for standalone testing but production needs real agent orchestration | Adds `LangGraphMultiAgentBackend` with supervisor sub-graph pattern; `MultiAgentCoordinator` switches backends via `use_langgraph_backend` config; automatic fallback to `SimulatedMultiAgentBackend` on any exception | Active |
| D022 | 2024-05-06 | Optional governance dashboard module (FastAPI + Jinja2) | Safety & Governance layer produces audit trails and violations but lacks operational visibility | Adds `aio/dashboard/` package with `AuditStore`, `create_dashboard_app`, and `runner.py`; entirely optional and disabled by default (`GOVERNANCE_DASHBOARD_ENABLE=false`); no impact on core graph when disabled | Active |
| D023 | 2024-05-07 | MCP (Model Context Protocol) integration as Priority 5 | Agents need to consume external tools exposed by MCP servers (e.g., filesystem, GitHub) without hardcoding adapters | Adds raw JSON-RPC 2.0 client with stdio and SSE transports; integrates into `ToolGate` behind `MCP_ENABLE` flag; namespaced tool names (`mcp/<server>/<tool>`); graceful degradation when server is unreachable; no new required dependencies (`httpx` already in `requirements.txt`) | Active |
| D024 | 2024-05-08 | Performance Benchmark Suite (`aio/benchmark/`) as Priority 6 | Core framework needs reproducible performance regression detection and CI-friendly benchmarking without modifying layer code | Adds `BenchmarkCollector` that monkey-patches `ObservabilityLayer` to intercept latencies/counts; `BenchmarkRunner` executes built-in scenarios against compiled graph; `JSONReporter` + `HTMLReporter` (Jinja2 fallback); `RegressionDetector` compares against baseline JSON; CLI exits non-zero on regression; all optional deps (`psutil`, `jinja2`) guarded with graceful degradation | Active |
| D025 | 2024-05-09 | Modern Python packaging & distribution via `pyproject.toml`, console scripts, multi-stage Dockerfile, and GitHub Actions CI/CD | Project matured to a point where installability, reproducible builds, containerized deployment, and automated publishing were required for adoption. Priority 7 was created to address these needs without breaking existing import paths. | `pyproject.toml` becomes the canonical dependency and build metadata source; `requirements.txt` deprecated. Package version starts at `7.0.0` (semantic versioning aligned with Priority 7). Console scripts `aio` and `aio-benchmark` provide first-class CLI entry points. Multi-stage Dockerfile reduces final image size and installs `[all]` extras. CI tests across Python 3.10–3.12; PyPI publishing uses OIDC trusted publishing; Docker publishing uses Buildx for multi-arch images. `MANIFEST.in` ensures non-Python data (prompts, dashboard templates, `.env.example`) are included in sdists. `aio_framework.py` is declared via `py-modules` so root-level backward-compatible imports continue to work. | Active |
| D026 | 2024-05-10 | Real-Time Cognitive Streaming & Event Layer (Priority 8) | AIO is batch-oriented with no visibility into cognition in flight. Operators and downstream UIs need live, structured events from every layer without blocking graph execution. | Adds `aio/streaming/` with `StreamEvent`, `StreamingManager`, `SSETransport`, `WebSocketTransport`, `EventStore`, and `MemoryTransport`. Nodes are wrapped via `_wrap_node` in `build_aio_graph()` to emit START/END/DATA events fire-and-forget. CLI gains `--stream` for NDJSON output. Dashboard gains `/ws/live` when both streaming and dashboard are enabled. All streaming is gated by `ENABLE_STREAMING` and fully backward compatible. Optional `websockets>=12.0` added to `pyproject.toml` extras. | Active |

---

## Status Definitions

- **Active**: Decision is current and governs active code.
- **Superseded**: Replaced by a later decision; retained for historical context.
- **Reverted**: Decision was undone; code no longer reflects it.

---

*Last updated: Post-PR #14 — Packaging & Distribution (Priority 7)*
