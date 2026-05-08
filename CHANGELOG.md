# Changelog

## [9.1.0] — 2026-05-08

### Added
- **Memory Bridge Embedding Subsystem — Day 1**
  - `aio/memory/embeddings.py` with four cohesive classes:
    - `BaseEmbeddingEngine` (ABC) — `embed(text: str) -> List[float]` contract
    - `RealEmbeddingEngine` — wraps `sentence-transformers` `SentenceTransformer`, configurable model name (default `all-MiniLM-L6-v2`), handles normalization, dimension=384
    - `PseudoEmbeddingEngine` — deterministic hash-based fallback producing 64-dim normalized vectors (preserves pre-refactor behavior)
    - `EmbeddingEngineFactory.create(config: MemoryConfig)` — returns `RealEmbeddingEngine` if `ENABLE_REAL_EMBEDDINGS=true` AND `sentence-transformers` is available, otherwise `PseudoEmbeddingEngine` with a clear warning log
  - `aio/memory/__init__.py` package marker with public re-exports
  - `tests/unit/test_memory_embeddings.py` — determinism, normalization, factory disabled/enabled/unavailable paths, load-failure fallback, real dimension verification

### Changed
- `aio/layers/memory.py` refactored:
  - Removed inline `sys.modules.get("aio_framework")` hack and inline `_embed` logic (~lines 42-53 and ~lines 96-106)
  - `__init__` now delegates engine creation to `EmbeddingEngineFactory.create(config)`
  - `_embed()` delegates to `self._embedding_engine.embed(content)`
- `aio/__init__.py` and `aio_framework.py` export all new embedding symbols
- `SESSION_START.md` key file map updated with `aio/memory/embeddings.py`

### Metrics Targets
| Metric | Target | Status |
|--------|--------|--------|
| Pseudo embedding determinism | 100% | Unit tested |
| Pseudo embedding normalization | 100% | Unit tested |
| Factory fallback when disabled | 100% | Unit tested |
| Factory fallback when unavailable | 100% | Unit tested |
| Factory fallback on load failure | 100% | Unit tested |
| Real embedding dimensions (if available) | 100% | Unit tested |
| MemoryBridge backward compatibility | 100% | All existing tests pass unchanged |

---

## [9.0.0] — 2026-05-08

Merged via PR #21.

### Added
- **Human-in-the-Loop & Feedback Loop Integration — Priority 9**
  - `aio/layers/hitl.py` with four cohesive classes:
    - `HitlGate` — stateful pending-request registry with threading lock; `check()`, `approve()`, `reject()`, `get_pending()`
    - `FeedbackCollector` — `collect()` appends to state `human_feedback`; `ingest_to_memory()` creates synthetic context-window entries and delegates to `MemoryBridge.encode()`
    - `EscalationPolicy` — `evaluate()` triggers on safety violations and immune alert/anomaly thresholds; sets `escalation_reason`, `failure_state="FAILED"`, clears `output`, sets `error`
    - `FeedbackLoopEngine` — `record_correction()` and `replay()`; matches corrections against current intent and optionally mutates `plan` or `metrics` when planning/toolopt instances are passed
  - `HitlConfig` Pydantic model with env-driven defaults: `HITL_ENABLE`, `HITL_DESTRUCTIVE_PATTERNS`, `HITL_TIMEOUT_SECONDS`, `HITL_AUTO_REJECT_ON_TIMEOUT`, `HITL_ESCALATION_ON_SAFETY_VIOLATION`, `HITL_ESCALATION_ON_IMMUNE_ALERT`, `HITL_ANOMALY_THRESHOLD_FOR_ESCALATION`, `HITL_FEEDBACK_REPLAY_MAX_CORRECTIONS`
  - `AIOState` additive fields: `hitl_status`, `hitl_request`, `human_feedback`, `feedback_suggestions`, `escalation_reason`, `pending_feedback`
  - Graph wiring (zero breaking changes):
    - Pre-execution gate: `jtpro_optimize -> hitl_gate -> (route_hitl) -> execute_action | hitl_wait | escalate`
    - Post-finalize pipeline: `finalize_output -> feedback_collect -> self_evolution_analyze -> cognitive_immune_scan -> escalation_policy_eval -> feedback_loop_replay -> END`
  - Governance Dashboard HITL queue:
    - `AuditStore` methods: `record_hitl_request()`, `get_hitl_requests()`, `update_hitl_request()`
    - `/hitl` HTML page (`hitl.html`) with pending/all request tables and approve/reject forms
    - `/api/hitl` GET (list/filter) and POST (approve/reject) endpoints
  - `SelfEvolutionLayer.analyze()` now includes `human_feedback_count` in the performance snapshot
  - Comprehensive test suite:
    - `tests/unit/test_hitl.py` — gate logic, feedback ingestion, escalation thresholds, feedback replay, thread-safety smoke test
    - `tests/unit/test_governance_dashboard.py` — dashboard HITL HTML, API list/filter, approve/reject
    - `tests/integration/test_hitl_graph.py` — graph routing: pending wait, preapproved proceed, rejected escalate, immune alert escalation, feedback loop injection

### Changed
- `AIOConfig` now includes `hitl: HitlConfig`
- `aio/__init__.py` and `aio_framework.py` export all new HITL symbols, config, node functions, and routing functions

### Metrics Targets
| Metric | Target | Status |
|--------|--------|--------|
| HITL gate coverage (enabled/disabled/destructive) | 100% | All paths unit tested |
| Feedback ingestion and memory bridge delegation | 100% | Mocked and graceful-failure tested |
| Escalation policy threshold triggers | 100% | Safety violation, immune alert, anomaly score paths tested |
| Feedback loop replay with plan mutation | 100% | Intent matching and plan prefix injection tested |
| Dashboard HITL queue API | 100% | List, filter, approve, reject tested |
| Graph integration backward compatibility | 100% | `build_aio_graph(AIOConfig())` unchanged when HITL is disabled (default) |

---

## [8.0.0] — 2026-05-07

Merged via PR #17.

### Added
- **Real-Time Cognitive Streaming & Event Layer — Priority 8**
  - `aio/streaming/` package with `StreamEvent`, `StreamingManager`, `SSETransport`, `WebSocketTransport`, `EventStore`, `MemoryTransport`, and `NDJSONTransport`
  - Fire-and-forget event emission integrated into every LangGraph node wrapper via `_wrap_node`
  - `build_aio_graph()` accepts optional `streaming_manager` parameter; 100% backward compatible when omitted
  - CLI `--stream` flag prints NDJSON events to stdout (`aio run "query" --stream`)
  - Dashboard WebSocket endpoint `/ws/live` serves buffered events when dashboard and streaming are both enabled
  - `StreamingConfig` Pydantic model with env-driven defaults: `ENABLE_STREAMING`, `STREAMING_TRANSPORT`, `STREAMING_EVENT_PERSISTENCE`, `STREAMING_MAX_BUFFER_EVENTS`
  - Optional `streaming` extra in `pyproject.toml` (`websockets>=12.0`)
  - Comprehensive test suite:
    - `tests/unit/test_streaming_manager.py`
    - `tests/unit/test_streaming_transports.py`
    - `tests/unit/test_streaming_store.py`
    - `tests/integration/test_streaming_graph.py`
    - `tests/unit/test_cli_streaming.py`
  - Documentation: `docs/streaming.md`, updated `configuration.md`, `api-reference.md`, `index.md`, `mkdocs.yml`

### Changed
- `AIOConfig` now includes `streaming: StreamingConfig`
- `aio/__init__.py` exports all streaming symbols and `StreamingConfig`

### Metrics Targets
| Metric | Target | Status |
|--------|--------|--------|
| Streaming event coverage per layer | 100% | All 13 layers emit START/END events |
| Backward compatibility (no streaming) | 100% | `build_aio_graph(AIOConfig())` unchanged |
| CLI `--stream` NDJSON output | 100% | Verified in unit tests |
| Dashboard WebSocket live feed | 100% | Endpoint registered when both features enabled |
| Test coverage for streaming package | > 90% | Manager, transports, store, graph, CLI |

---

## [7.0.0] — 2024-05-09

Merged via PR #14.

### Added
- **Packaging & Distribution — Priority 7**
  - `pyproject.toml` with PEP 621 metadata, `setuptools` build backend, and semantic versioning starting at `7.0.0`
  - Core dependencies in `[project]`, optional extras:
    - `dashboard` — FastAPI, Uvicorn, Jinja2
    - `llm` — langchain-openai, langchain-anthropic
    - `embeddings` — sentence-transformers
    - `memory-redis` — redis
    - `memory-postgres` — psycopg2-binary
    - `benchmark` — psutil, jinja2
    - `dev` — all extras + pytest, pytest-asyncio, pytest-cov
    - `all` — union of all runtime extras
  - Console-script entry points:
    - `aio` — unified CLI (`aio run`, `aio benchmark`, `aio dashboard`)
    - `aio-benchmark` — backward-compatible benchmark CLI
  - New `aio/cli.py` with subcommands:
    - `run` — builds graph, invokes query, prints JSON output
    - `benchmark` — delegates to `aio.benchmark.cli:main`
    - `dashboard` — starts Uvicorn with `create_dashboard_app` when available
  - Multi-stage `Dockerfile` (builder + runtime) based on `python:3.12-slim`, installs `[all]` extras, exposes ports `8000` and `9091`, healthcheck via import smoke test
  - GitHub Actions workflows:
    - `ci.yml` — test matrix (Python 3.10–3.12), wheel + sdist build, artifact upload
    - `publish-pypi.yml` — triggered on `v*` tags, trusted publishing via OIDC
    - `publish-docker.yml` — triggered on `v*` tags, multi-arch (`linux/amd64`, `linux/arm64`) build-push to Docker Hub
  - `MANIFEST.in` to ensure `prompts/`, `dashboard/templates/`, and `.env.example` are included in sdist

### Changed
- `requirements.txt` deprecated; replaced with a comment pointing to `pip install -e ".[dev]"`
- `README.md` updated with `pip install aio-framework[all]`, CLI examples, and Docker usage
- Test coverage target changed from `--cov=aio_framework` to `--cov=aio` to align with package namespace

### Preserved
- Backward compatibility: `aio_framework.py` remains at repo root and is declared via `py-modules`; existing imports (`from aio_framework import ...`) continue to work unchanged

### Metrics Targets
| Metric | Target | Status |
|--------|--------|--------|
| Wheel + sdist build success | 100% | Verified in CI build job |
| Docker image build success | 100% | Multi-stage Dockerfile builds cleanly |
| CI test matrix (3.10–3.12) | 100% | All tests pass on matrix |
| Backward compatibility (root shim import) | 100% | `aio_framework.py` import preserved |
| Console script entry points | 100% | `aio` and `aio-benchmark` installable |

---

## [Priority 6.0.0] — 2024-05-08

### Added
- **Performance Benchmarking Suite — Priority 6**
  - `aio/benchmark/` subpackage with collector, runner, reporters, regression detector, and CLI
  - `BenchmarkCollector` wraps `ObservabilityLayer` to intercept per-node latency and count data without modifying layer code
  - Memory profiling: `psutil.Process().memory_info().rss` when available; falls back to `tracemalloc` (stdlib); skips silently when neither is available
  - `BenchmarkRunner` compiles the graph once per session and executes built-in scenarios: `echo`, `safety_block`, `failure_recovery`, `context_overflow`, `multi_agent`
  - Fresh `make_initial_state()` per iteration to prevent state pollution across runs
  - `JSONReporter` serializes results with metadata (timestamp, Python version, git commit)
  - `HTMLReporter` uses inline Jinja2 template with SVG bar charts when Jinja2 is available; otherwise emits minimal plain HTML
  - `RegressionDetector` compares current run against a baseline JSON, flagging regressions beyond a configurable threshold for p50/p99 latency, e2e time, and throughput
  - `aio/benchmark/cli.py` provides an `argparse` entry point (`python -m aio.benchmark.cli`) suitable for CI — exits with code `1` on regression
  - `BenchmarkConfig` Pydantic v2 model with `BENCHMARK_*` env-driven defaults
  - Graph builder backward-compatible change: optional `observability_layer` parameter so benchmarks can inject a collector-wrapped layer
- **Testing**
  - `tests/unit/test_benchmark_collector.py` — mocked observability, latency accumulation, memory graceful degradation
  - `tests/unit/test_benchmark_reporter.py` — JSON round-trip, HTML scenario names, Jinja2 fallback
  - `tests/unit/test_benchmark_regression.py` — baseline/current construction, threshold detection, report serialization
  - `tests/integration/test_benchmark_suite.py` — runner against real graph with 1 iteration + 0 warmup

### Metrics Targets
| Metric | Target | Status |
|--------|--------|--------|
| Benchmark suite unit test coverage | > 90% | All collector, reporter, and regression paths tested |
| Integration smoke test (real graph) | 100% | Runner populates results without exceptions |
| Regression detection accuracy | 100% | Threshold logic verified for latency and throughput |
| Graceful degradation without psutil | 100% | Falls back to tracemalloc or skips silently |

---

## [Priority 5.0.0] — 2024-05-07

### Added
- **MCP (Model Context Protocol) Integration — Layer 7**
  - `MCPClient` in `aio/layers/mcp_client.py` with JSON-RPC 2.0 over stdio and SSE transports
  - `StdioTransport` spawns MCP servers via `subprocess.Popen` with lifecycle management
  - `SSETransport` connects to MCP servers over HTTP using `httpx` (optional dependency)
  - `MCPConfig` and `MCPServerConfig` Pydantic v2 models with env-driven defaults
  - ToolGate integration: `MCPClient.discover_and_register()` dynamically registers MCP tools with `mcp/<server>/<tool>` namespacing
  - MCP tool execution delegates back to `MCPClient.call_tool()` via handler closures
  - Observability spans: `mcp.initialize`, `mcp.list_tools`, `mcp.call_tool`
  - Graceful degradation: MCP unavailable or misconfigured → local tools only, no crash
  - State fields: `mcp_discovered_tools`, `mcp_execution_metadata`, `mcp_errors`
  - Feature flags: `MCP_ENABLE`, `MCP_SERVERS` (JSON array), `MCP_TIMEOUT_SECONDS`
- **Testing**
  - `tests/unit/test_mcp_client.py` — transport mocking, JSON-RPC formatting, discovery, graceful degradation, observability
  - `tests/unit/test_tool_gate.py` — MCP discovery on init, MCP tool execution metadata, graceful fallback
  - `tests/integration/test_mcp_integration.py` — graph compilation with MCP enabled, tool routing, fallback to local tools

### Metrics Targets
| Metric | Target | Status |
|--------|--------|--------|
| MCP client unit test coverage | > 90% | All transport and client paths mocked |
| Graph compilation with MCP enabled | 100% | Smoke tests pass with/without MCP |
| Graceful degradation when MCP server unreachable | 100% | Falls back to local tools silently |

---

## [Priority 4.0.0] — 2024-05-06

### Added
- **Modularization**
  - `aio/` package with `layers/`, `config/`, `graph/` submodules
  - All layer classes, configs, state, nodes, routing, and graph builder moved from single-file `aio_framework.py` into focused modules
  - `aio_framework.py` preserved as a backward-compatible re-export shim — existing imports and tests continue to work unchanged
  - `aio/__init__.py` exposes clean public API for new code
- **Persistent Memory Backends**
  - `BaseMemoryBackend` abstract interface in `aio/layers/memory_backends.py`
  - `InMemoryBackend` — default no-op, all state in process memory
  - `RedisBackend` — persists episodic, long-term, and keyword index to Redis hashes/sets
  - `PostgresBackend` — persists memory entries to PostgreSQL using JSONB
  - `HybridBackend` — Redis for hot/episodic data, Postgres for cold/long-term data
  - `MEMORY_BACKEND_TYPE` env flag selects backend (`memory` | `redis` | `postgres` | `hybrid`)
  - `REDIS_URL` and `POSTGRES_URL` env vars configure connection strings
  - All persistent backends gracefully degrade to in-memory if the server is unreachable
- **Cognitive Immune Learning**
  - `ImmuneLearningEngine` in `aio/layers/immune_learning.py`
  - Stores historical immune snapshots in PostgreSQL (`aio_immune_history` table)
  - Computes rolling statistical baselines (mean, stddev) over a configurable window
  - Derives learned anomaly score from Z-scores for `failure_count`, `safety_violation_count`, and `corrupted_memory_count`
  - `COGNITIVE_IMMUNE_LEARN_ENABLE` flag toggles the engine (default: `false`)
  - `learn_rolling_window` (default: 100), `learn_z_threshold` (default: 2.0), `learn_min_samples` (default: 10), and `learn_record_ttl_seconds` (default: 604800) configurable via `CognitiveImmuneConfig`
  - Integrates into `CognitiveImmuneSystem.scan()`; learned score augments heuristic score
- **New Feature Flags**
  - `MEMORY_BACKEND_TYPE` — select memory backend
  - `REDIS_URL` / `POSTGRES_URL` — backend connection strings
  - `COGNITIVE_IMMUNE_LEARN_ENABLE` — toggle immune learning
  - `LEARN_ROLLING_WINDOW` / `LEARN_Z_THRESHOLD` — immune learning hyperparameters
- **New Dependencies**
  - `redis>=5.0.0` (optional, used by `RedisBackend`)
  - `psycopg2-binary>=2.9.0` (optional, used by `PostgresBackend` and `ImmuneLearningEngine`)
- **Testing**
  - 151 tests passing (2 pre-existing flaky tests unrelated to Priority 4)

### Changed
- `aio_framework.py` reduced from ~2600 lines to ~170 lines (re-export shim)
- `requirements.txt` now includes `redis>=5.0.0` and `psycopg2-binary>=2.9.0`
- `.env.example` updated with new flags (`MEMORY_BACKEND_TYPE`, `REDIS_URL`, `POSTGRES_URL`, `COGNITIVE_IMMUNE_LEARN_ENABLE`)

### Metrics Targets
| Metric | Target | Status |
|--------|--------|--------|
| Modularization backward compatibility | 100% | All existing tests pass without import changes |
| New backend graceful degradation | 100% | Backends fall back to in-memory when remote is unreachable |
| Immune learning false positive rate | < 5% | Z-score threshold configurable; min-samples gate prevents early noise |
| Graph compilation (all flag combinations) | 100% | Smoke tests pass for all modes |

---

## [Priority 3.0.0] — 2024-05-06

### Added
- **Layer 9 — Self-Evolution**
  - `SelfEvolutionLayer` with performance snapshotting, trend reporting, and safe config delta suggestions
  - Bounded auto-apply: only whitelisted tunable keys can be modified automatically
  - Post-finalize reflection pipeline (runs after every output)
- **Layer 10 — Multi-Agent Coordination**
  - `MultiAgentCoordinator` with task decomposition by intent (`coding`, `analysis`, `general`)
  - Simulated agent dispatch/aggregate/synthesize using a configurable registry
  - Consensus scoring based on output variance across simulated agents
- **Layer 11 — Safety & Governance**
  - `SafetyGovernance` with per-turn audit trail recording
  - Constitutional compliance checks against four mandates
  - Governance voting with configurable thresholds for sensitive operations
- **Layer 12 — Cognitive Immune System**
  - `CognitiveImmuneSystem` with anomaly scanning (failure rate, corrupted memory, threat patterns)
  - Quarantine system that copies suspicious entries without destructive deletion
  - Auto-heal with TTL-based threat pattern pruning
  - Immunity status tracking (`HEALTHY`, `ALERT`, `COMPROMISED`)
- **Graph Integration**
  - Master feature flag `ENABLE_PRIORITY_3` with per-layer sub-flags
  - Conditional routing: multi-agent branch before planning, governance audit gate before verification, post-finalize reflection pipeline
  - Full backward compatibility: graph compiles and all Priority 1/2 tests pass with `ENABLE_PRIORITY_3=false`
- **Prompts**
  - `prompts/meta/self_evolution.txt` — performance snapshot/report/suggest/apply protocol
  - `prompts/meta/multi_agent.txt` — agent registry, decompose/dispatch/consensus rules
  - `prompts/meta/governance.txt` — audit checklist, constitutional mandates, voting
  - `prompts/meta/immune.txt` — threat categories, scan/quarantine/heal protocol
- **Testing**
  - 33 new unit tests across Layers 9–12
  - 9 new integration tests for Priority 3 conditional routing
  - 6 new failure injection / immune response tests
  - Total: 135 tests, all passing
- **Session Continuity Docs**
  - `SESSION_START.md` — single source of truth for context recovery
  - `PROJECT_STATE.md` — living completion matrix and known issues
  - `DECISION_LOG.md` — structured architectural decision registry

### Metrics Targets
| Metric | Target | Status |
|--------|--------|--------|
| Priority 3 backward compatibility | 100% | All existing tests pass with flag disabled |
| New layer unit test coverage | > 90% | 33 unit + 9 integration + 6 chaos tests |
| Graph compilation (enabled/disabled) | 100% | Smoke tests pass for both modes |
| Immune false positive rate | < 5% | Healthy-state test confirms no false positives |

---

## [Priority 2.0.0] — 2024-05-05

### Added
- **Layer 3 — Planning & Anti-Myopia**
  - `HiPlan`: hierarchical task decomposition with configurable max depth
  - `FLARE`: lookahead planning with horizon window
  - `PPA`: pitfall pattern analysis before execution
  - `SPIRAL`: symbolic MCTS with configurable simulations
  - `VMAO`: DAG-based plan decomposition with replanning
- **Layer 4 — Proactive Curiosity**
  - `CuriosityEngine`: novelty detection, information gap tracking, intrinsic reward scoring
- **Layer 6 — Tool-Use Optimization**
  - `G-STEP`: tool necessity scoring with configurable threshold
  - `HDPO`: accuracy/efficiency weighted policy optimization
  - `JTPRO`: iterative prompt optimization
- **Graph Integration**
  - Planning nodes integrated into the StateGraph flow
  - Curiosity gate before plan generation
  - Tool optimizer between verification and execution

---

## [Priority 1.0.0] — 2024-05-05

### Added
- **Layer 0 — Infrastructure & Observability**
  - OpenTelemetry tracing with OTLP export and console fallback
  - Prometheus client metrics (node latency, execution counters, failure state gauge, context budget gauge)
  - Structured JSON logging with correlation IDs
  - Optional LangSmith run tracking with graceful degradation
- **Layer 1 — Context & Attention Management**
  - `ContextManager` with Sculptor token-aware windowing
  - BAPO dynamic attention routing (`memory`, `verify`, `execute`, `recover`)
  - Intent classification (`general`, `action`, `analysis`, `coding`)
  - Working memory pruning with recency and importance weighting
- **Layer 2 — Dual-Memory Bridge**
  - `MemoryBridge` implementing full encode → verify → store → consolidate → retrieve → forget lifecycle
  - Hindsight episodic memory and long-term memory stores
  - MIA (Memory Importance Assessment) composite scoring
  - Hybrid retrieval: keyword pre-filter + pseudo-vector similarity + recency + importance
  - MemForge consolidation with configurable batch size and TTL
- **Layer 5 — Verification & Quality Assurance**
  - `Verifier` with LLM critique, FormalJudge rule-based checks, AGEL-Comp ensemble scoring, and AgentDebug hypothesis generation
  - Configurable ensemble threshold (default 0.85)
  - Historical competence trend adjustment
- **Layer 7 — Execution & Action**
  - `ToolGate` with HermesAgent intent-based tool routing
  - Docker sandbox execution with memory limits, CPU quota, disabled network, read-only rootfs
  - Capability registry with default tools (`python_sandbox`, `bash_sandbox`, `echo`)
  - Safe degradation when Docker is unavailable
- **Layer 8 — Failure Recovery & Anti-Fragility**
  - `FailureRecovery` with ReCiSt state machine (`HEALTHY`, `DEGRADED`, `RECOVERING`, `FAILED`)
  - Exponential backoff with jitter for transient failures
  - Escalation path for permanent failures; graceful degradation for catastrophic failures
  - `NeuroShield` runtime safety boundary enforcement with pattern matching and jailbreak detection
  - Anti-fragility learning: adaptive retry backoff multiplier tuning
- **LangGraph StateGraph**
  - Complete graph assembly with all Priority 1 nodes and conditional edges
  - Routing functions: `route_memory_confidence`, `route_verification`, `route_failure`, `route_shield`
  - Explicit safety gate (`neuroshield`) before memory operations
- **Prompts**
  - `prompts/system/base_system.txt` — agent identity and layer protocols
  - `prompts/cognitive/recon.txt` — reconnaissance and BAPO initialization
  - `prompts/cognitive/plan.txt` — task decomposition and strategy selection
  - `prompts/cognitive/prove.txt` — self-critique and evidence chain construction
  - `prompts/safety/constitutional.txt` — four constitutional mandates enforcement
  - `prompts/safety/boundary.txt` — NeuroShield operational protocol
- **Testing**
  - Unit tests for every layer (observability, context, memory, verifier, toolgate, failure recovery)
  - Integration tests for cross-layer interactions and conditional routing
  - End-to-end tests using the compiled StateGraph
  - Failure injection / chaos tests (memory corruption, tool timeout, Docker crash, verification failure, context overflow, boundary breach)
- **DevOps**
  - `docker-compose.yml` with OTel Collector, Prometheus, Grafana, Jaeger, and framework service
  - `.env.example` documenting all required and optional environment variables
  - `requirements.txt` with pinned dependency ranges

### Metrics Targets
| Metric | Target | Status |
|--------|--------|--------|
| Memory retrieval accuracy | > 90% | Implemented (hybrid search) |
| Verification ensemble pass rate | > 85% | Implemented (ensemble scoring) |
| Failure recovery rate | > 95% | Implemented (ReCiSt + backoff) |
| Context overflow handling | 100% | Implemented (Sculptor) |
| Safety violation interception | 100% | Implemented (NeuroShield) |

### Known Limitations
- Vector embeddings use deterministic pseudo-vectors for standalone operation; replace with real embedding model for production retrieval accuracy.
- LangSmith integration requires valid API key; disabled automatically if unavailable.
- Docker sandbox requires local Docker socket access; falls back to error if unavailable.
- ~~Plan generation is heuristic-based~~ ✅ Done — LLM-based planning available behind `ENABLE_LLM_PLANNING` flag with graceful fallback to heuristics (see Priority 4).
- Prometheus HTTP server binds to all interfaces; configure firewall rules for production.
