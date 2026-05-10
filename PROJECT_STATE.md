# PROJECT_STATE.md — Persistent Project State

> **Purpose**: Living document tracking completion, coverage, known issues, and ordered next steps. Update this after every significant change.

---

## 1. Layer Completion Matrix

| Layer | Name | Class | Config | State Fields | Node Wrapper | Routing | Unit Tests | Status |
|-------|------|-------|--------|-------------|--------------|---------|-----------|--------|
| 0 | Observability | `ObservabilityLayer` | `ObservabilityConfig` | — | — | — | `test_observability.py` | ✅ Complete |
| 1 | Context | `ContextManager` | `ContextConfig` | `intent`, `context_window`, `context_budget`, `attention_map` | `node_context_*` | `route_context_priority` | `test_context_manager.py` | ✅ Complete |
| 2 | Memory | `MemoryBridge` | `MemoryConfig` | `working_memory`, `long_term_memory`, `memory_confidence` | `node_memory_*` | `route_memory_confidence` | `test_memory_bridge.py` | ✅ Complete |
| 3 | Planning | `PlanningLayer` + sub-planners | `PlanningConfig` | `plan`, `hierarchical_plan`, `lookahead_result`, `fact_augmented_plan`, `pitfall_analysis`, `spiral_tree`, `mars_reflection`, `maci_meta_plan`, `vmao_dag` | `node_*` | `route_ppa` | (covered in integration) | ✅ Complete |
| 4 | Curiosity | `CuriosityEngine` | `CuriosityConfig` | `curiosity_score`, `novelty_map`, `information_gaps` | `node_curiosity_*` | — | (covered in integration) | ✅ Complete |
| 5 | Verification | `Verifier` | `VerifierConfig` | `verification_result` | `node_verify_plan` | `route_verification` | `test_verifier.py` | ✅ Complete |
| 6 | Tool Optimization | `ToolOptimizer` | `ToolOptimizerConfig` | `tool_necessity_score`, `tool_policy_channels`, `tool_prompt_optimization`, `sandbox_result`, `tool_analytics` | `node_gstep_*`, etc. | `route_gstep` | `test_tool_gate.py` | ✅ Complete |
| 7 | Execution | `ToolGate` + `MCPClient` | `ToolGateConfig` + `MCPConfig` | `execution_result`, `mcp_discovered_tools`, `mcp_execution_metadata`, `mcp_errors` | `node_execute_action` | — | `test_tool_gate.py`, `test_mcp_client.py` | ✅ Complete |
| 8 | Failure Recovery | `FailureRecovery` | `FailureRecoveryConfig` | `failure_state`, `failure_count`, `retry_budget`, `safety_violations` | `node_failure_*` | `route_failure`, `route_shield` | `test_failure_recovery.py` | ✅ Complete |
| 9 | Self-Evolution | `SelfEvolutionLayer` | `SelfEvolutionConfig` | `self_evolution_report`, `performance_snapshot`, `suggested_config_delta` | `node_self_evolution_analyze` | `route_self_evolution` | `test_self_evolution.py` | ✅ Complete |
| 10 | Multi-Agent Coordination | `MultiAgentCoordinator` | `MultiAgentConfig` | `coordination_plan`, `agent_outputs`, `consensus_score` | `node_multi_agent_*` | `route_multi_agent` | `test_multi_agent.py` | ✅ Complete |
| 11 | Safety & Governance | `SafetyGovernance` | `SafetyGovernanceConfig` | `audit_trail`, `governance_result`, `compliance_violations` | `node_safety_governance_audit` | `route_safety_governance` | `test_safety_governance.py` | ✅ Complete |
| 12 | Cognitive Immune System | `CognitiveImmuneSystem` | `CognitiveImmuneConfig` | `immune_status`, `anomaly_score`, `quarantined_ids`, `healing_actions`, `threat_patterns_detected` | `node_cognitive_immune_scan` | `route_post_finalize` | `test_cognitive_immune.py` | ✅ Complete |
| 6 | Benchmark Suite | `BenchmarkRunner` | `BenchmarkConfig` | — | — | — | `test_benchmark_collector.py`, `test_benchmark_reporter.py`, `test_benchmark_regression.py`, `test_benchmark_suite.py` | ✅ Complete |
| — | Packaging & Distribution | — | — | — | — | — | CI / smoke tests | ✅ Complete |
| — | Streaming & Event Layer | `StreamingManager` | `StreamingConfig` | — | `_wrap_node` | — | `test_streaming_manager.py`, `test_streaming_transports.py`, `test_streaming_store.py`, `test_streaming_graph.py`, `test_cli_streaming.py` | ✅ Complete |
| 9 | HITL & Feedback Loop | `HitlGate`, `FeedbackCollector`, `EscalationPolicy`, `FeedbackLoopEngine` | `HitlConfig` | `hitl_status`, `hitl_request`, `human_feedback`, `feedback_suggestions`, `escalation_reason`, `pending_feedback` | `node_hitl_gate`, `node_hitl_wait`, `node_feedback_collect`, `node_escalation_policy`, `node_feedback_loop` | `route_hitl`, `route_escalation_policy` | `test_hitl.py`, `test_governance_dashboard.py` (HITL), `test_hitl_graph.py` | ✅ Complete |

---

## 2. Test Coverage Matrix

| Test File | What It Tests | Priority |
|-----------|--------------|----------|
| `tests/unit/test_observability.py` | OTel spans, Prometheus metrics, logging, null context | 1 |
| `tests/unit/test_context_manager.py` | Ingest, sculpt, attention routing, intent classification | 1 |
| `tests/unit/test_memory_bridge.py` | Encode, verify, store, consolidate, retrieve, forget | 1 |
| `tests/unit/test_verifier.py` | Critique, judge, score, debug, ensemble threshold | 1 |
| `tests/unit/test_tool_gate.py` | Tool registry, routing, Docker sandbox, direct run | 1 |
| `tests/unit/test_failure_recovery.py` | Assess, retry, shield, learn, state transitions | 1 |
| `tests/unit/test_self_evolution.py` | Analyze, report, suggest, apply with mocked observability | 3 |
| `tests/unit/test_multi_agent.py` | Decompose, dispatch, aggregate, synthesize, registry | 3 |
| `tests/unit/test_safety_governance.py` | Audit, compliance, vote, record with constitutional checks | 3 |
| `tests/unit/test_cognitive_immune.py` | Scan, detect, quarantine, heal, update with anomaly injection | 3 |
| `tests/unit/test_llm_planner.py` | LLM planner fallback, mocked OpenAI/Anthropic, JSON parsing, observability counts | 4 |
| `tests/integration/test_layer_interactions.py` | Cross-layer state propagation | 1 |
| `tests/integration/test_end_to_end.py` | Full graph compilation, echo, safety, multi-turn, failure, overflow | 1+2 |
| `tests/integration/test_priority3_routing.py` | Conditional routing with `enable_priority_3` true/false | 3 |
| `tests/failure_injection/test_chaos.py` | Memory corruption, tool timeout, Docker crash, verification failure, overflow, boundary breach, retry exhaustion | 1+2 |
| `tests/failure_injection/test_immune_response.py` | Memory corruption quarantine, rapid failure escalation, auto-heal, threat pattern persistence | 3 |
| `tests/integration/test_multi_agent_backend.py` | LangGraph backend dispatch, fallback, and graph integration | 4 |
| `tests/unit/test_governance_dashboard.py` | FastAPI routes, `AuditStore` ingestion, and `SafetyGovernance` integration | 4 |
| `tests/unit/test_mcp_client.py` | MCP transport mocking, JSON-RPC formatting, discovery, graceful degradation, observability | 5 |
| `tests/integration/test_mcp_integration.py` | Graph compilation with MCP enabled, tool routing, fallback to local tools | 5 |
| `tests/unit/test_benchmark_collector.py` | Latency accumulation, count interception, memory graceful degradation | 6 |
| `tests/unit/test_benchmark_reporter.py` | JSON round-trip, HTML scenario names, Jinja2 fallback | 6 |
| `tests/unit/test_benchmark_regression.py` | Baseline comparison, threshold detection, report serialization | 6 |
| `tests/integration/test_benchmark_suite.py` | Real graph execution, scenario coverage, result population | 6 |
| `tests/unit/test_streaming_manager.py` | Subscribe, emit, buffer, unsubscribe, exception isolation, event factory | 8 |
| `tests/unit/test_streaming_transports.py` | MemoryTransport, SSETransport, WebSocketTransport, NDJSONTransport | 8 |
| `tests/unit/test_streaming_store.py` | EventStore memory backend, Redis fallback, replay with trace_id filter | 8 |
| `tests/integration/test_streaming_graph.py` | Graph compilation with/without streaming_manager, START/END event coverage | 8 |
| `tests/unit/test_cli_streaming.py` | CLI `--stream` NDJSON output, `--no-stream` single JSON output | 8 |
| `tests/unit/test_hitl.py` | HitlGate gating, FeedbackCollector ingestion, EscalationPolicy thresholds, FeedbackLoopEngine replay | 9 |
| `tests/unit/test_governance_dashboard.py` (HITL) | Dashboard `/hitl` HTML, `/api/hitl` list/filter/approve/reject | 9 |
| `tests/integration/test_hitl_graph.py` | Graph routing with HITL enabled: pending wait, preapproved proceed, rejected escalate, immune alert escalation, feedback loop injection | 9 |
| `tests/unit/test_pgvector_backend.py` | PostgresBackend schema creation, vector search SQL, hybrid search weights, pgvector unavailable fallback, connection failure | 10 |
| `tests/integration/test_memory_pgvector.py` | Full encode→verify→store→retrieve flow with real Postgres (skipped if unavailable) | 10 |

---

## 3. Known Issues / Limitations

1. **Real embedding support behind feature flag**: `sentence-transformers` integration is available via `ENABLE_REAL_EMBEDDINGS=true`. When disabled (default) or when the library is unavailable, deterministic pseudo-embeddings are used as fallback. Mixing real and pseudo vectors in the same memory store may yield inconsistent similarity scores if the flag is toggled mid-session.
2. **LangSmith requires valid API key**: Disabled automatically if unavailable.
3. **Docker sandbox requires local socket**: Falls back to graceful error if unavailable.
4. ~~Plan generation is heuristic-based~~ ✅ Done — LLM-based planning available behind `ENABLE_LLM_PLANNING` flag with graceful fallback to heuristics.
5. **Prometheus binds to all interfaces**: Configure firewall rules for production.
6. ~~Single-file growth~~ ✅ Done — `aio_framework.py` modularized into `aio/` package with `layers/`, `config/`, `graph/` submodules (see `DECISION_LOG.md`).
7. ~~Multi-agent dispatch is simulated~~ ✅ Done — real LangGraph backend available via `MULTI_AGENT_USE_LANGGRAPH_BACKEND`; simulated backend used as fallback.
8. **Self-evolution auto-apply is bounded**: Only whitelisted config keys can be modified automatically.
9. **MCP server sandboxing is the operator's responsibility**: MCP tools run in the MCP server's process; external sandboxing (e.g., Docker, firejail) should be configured by the operator.
10. **`requirements.txt` is deprecated**; development installs should use `pip install -e ".[dev]"`.
11. **Docker multi-arch builds** (`linux/amd64`, `linux/arm64`) require Docker Buildx; local builds default to host architecture.
12. ~~CLI commands do not yet have dedicated unit tests~~ ✅ Done — `tests/unit/test_cli_streaming.py` covers NDJSON streaming output.
13. **HITL wait requires external re-invocation**: When `hitl_status` is `"pending"`, the graph ends at `hitl_wait` → `END`. The external operator must approve via the dashboard/API and re-invoke the graph with `hitl_status="approved"`. This is deterministic and avoids LangGraph async interruption complexity.
14. ~~Day 1 complete but embedding engine is dimension-agnostic~~ ✅ Done — `PostgresBackend` now uses `vector(384)` columns with `vector_dimension=384` default, matching `RealEmbeddingEngine.dimension`.

---

## 4. In-Flight Work

> Priority 10 — Memory Upgrade (4-Day Plan)
> - Day 1: Real Embedding Engine ✅ Complete — PR #25
> - Day 2: Persistent Storage (PostgreSQL + pgvector) ✅ Complete — PR #26
> - Day 3: True Memory Lifecycle (LLM consolidation, Ebbinghaus forgetting) — Pending
> - Day 4: Integration & Tool Exposure (store_memory, recall_memory tools) — Pending

---

## 5. Ordered Next Steps (Post-Priority 6)

1. ~~Modularize `aio_framework.py`~~ ✅ Done — split into `aio/` package with `layers/`, `config/`, `graph/` submodules.
2. ~~Real embedding integration~~ ✅ Done — integrated behind `ENABLE_REAL_EMBEDDINGS` flag.
3. ~~LLM-based planning~~ ✅ Done — integrated behind `ENABLE_LLM_PLANNING` flag with optional `langchain-openai` / `langchain-anthropic` providers.
4. ~~Persistent memory backend~~ ✅ Done — `InMemoryBackend`, `RedisBackend`, `PostgresBackend`, `HybridBackend` behind `MEMORY_BACKEND_TYPE` flag.
5. ~~Cognitive immune system learning~~ ✅ Done — `ImmuneLearningEngine` with PostgreSQL storage, rolling baselines, Z-score anomaly detection behind `COGNITIVE_IMMUNE_LEARN_ENABLE` flag.
6. ~~Multi-agent real dispatch~~ ✅ Done — LangGraph supervisor/hierarchical sub-graph backend integrated behind `MultiAgentCoordinator`; simulated backend remains as fallback.
7. ~~Governance dashboard~~ ✅ Done — FastAPI/Jinja2 dashboard with `AuditStore`, summary page, session detail, and REST API endpoints.
8. ~~MCP integration~~ ✅ Done — `MCPClient` with stdio/SSE transports, JSON-RPC 2.0, dynamic tool discovery, ToolGate delegation behind `MCP_ENABLE` flag.
9. ~~Benchmark Suite~~ ✅ Done — `aio/benchmark/` subpackage with collector, runner, reporters, regression detector, and CLI.
10. ~~Packaging & Distribution~~ ✅ Done — `pyproject.toml`, CLI, Dockerfile, CI/CD workflows.
11. ~~Real-Time Cognitive Streaming~~ ✅ Done — `aio/streaming/` package with manager, transports, store, graph integration, CLI `--stream`, dashboard `/ws/live`.
12. ~~Human-in-the-Loop & Feedback Loop~~ ✅ Done — `HitlGate`, `FeedbackCollector`, `EscalationPolicy`, `FeedbackLoopEngine`, `HitlConfig`, dashboard `/hitl` queue, graph wiring, tests.
13. ~~Day 1: Real Embedding Engine~~ ✅ Done — extracted `RealEmbeddingEngine`/`PseudoEmbeddingEngine` into `aio/memory/embeddings.py` behind `ENABLE_REAL_EMBEDDINGS` flag with graceful fallback.
14. ~~Day 2: Persistent Storage with pgvector~~ ✅ Done — `PostgresBackend` upgraded with `vector(384)` columns, HNSW index, `vector_search`, `hybrid_search`, and graceful JSONB fallback.
15. Day 3: True Memory Lifecycle — LLM-based episodic consolidation, adaptive Ebbinghaus forgetting curve.
16. Day 4: Integration & Tool Exposure — `store_memory` and `recall_memory` tools registered in ToolGate.

---

## 6. Environment / Dependency Snapshot

```
requires-python = ">=3.10"
```

**Core dependencies (from `pyproject.toml` `[project] dependencies`):**
- `langgraph>=0.0.50`
- `langchain>=0.1.0`
- `langchain-core>=0.1.0`
- `langsmith>=0.1.0`
- `opentelemetry-api>=1.22.0`, `opentelemetry-sdk>=1.22.0`, `opentelemetry-exporter-otlp>=1.22.0`, `opentelemetry-instrumentation>=0.43b0`
- `prometheus-client>=0.19.0`
- `docker>=7.0.0`
- `pydantic>=2.0.0`
- `typing-extensions>=4.8.0`
- `httpx>=0.25.0`

**Optional extras (from `pyproject.toml` `[project.optional-dependencies]`):**
- `dashboard` — `fastapi>=0.110.0`, `uvicorn>=0.25.0`, `jinja2>=3.0.0`
- `llm` — `langchain-openai>=0.1.0`, `langchain-anthropic>=0.1.0`
- `embeddings` — `sentence-transformers>=2.2.0`
- `memory-redis` — `redis>=5.0.0`
- `memory-postgres` — `psycopg2-binary>=2.9.0`
- `benchmark` — `psutil>=5.9.0`, `jinja2>=3.0.0`
- `streaming` — `websockets>=12.0`
- `dev` — `aio-framework[all]`, `pytest>=7.4.0`, `pytest-asyncio>=0.21.0`, `pytest-cov>=4.1.0`
- `all` — union of all runtime extras

> **Note:** `requirements.txt` is deprecated. Use `pip install -e ".[dev]"` for development installs.

---

## 7. Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `ENABLE_PRIORITY_3` | `true` | Master switch for Layers 9-12 |
| `SELF_EVOLUTION_ENABLE` | `true` | Layer 9 enable |
| `MULTI_AGENT_ENABLE` | `true` | Layer 10 enable |
| `SAFETY_GOVERNANCE_ENABLE` | `true` | Layer 11 enable |
| `COGNITIVE_IMMUNE_ENABLE` | `true` | Layer 12 enable |
| `ENABLE_REAL_EMBEDDINGS` | `false` | Use `sentence-transformers` for real embeddings (fallback to pseudo-embeddings if unavailable) |
| `ENABLE_LLM_PLANNING` | `false` | Use LangChain LLM providers for base plan, HiPlan, FLARE, and PPA (fallback to heuristics if unavailable or disabled) |
| `MEMORY_BACKEND_TYPE` | `memory` | MemoryBridge backend: `memory` (in-process), `redis`, `postgres`, `hybrid` |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string for `RedisBackend` |
| `POSTGRES_URL` | `postgresql://localhost/aio` | PostgreSQL connection string for `PostgresBackend` and `ImmuneLearningEngine` |
| `PGVECTOR_ENABLE` | `true` | Enable pgvector extension and vector-native schema in `PostgresBackend` |
| `VECTOR_DIMENSION` | `384` | Embedding dimension used for pgvector schema creation |
| `COGNITIVE_IMMUNE_LEARN_ENABLE` | `false` | Enable `ImmuneLearningEngine` learned anomaly detection |
| `LEARN_ROLLING_WINDOW` | `100` | Rolling window size for immune learning baselines (read via `CognitiveImmuneConfig`) |
| `LEARN_Z_THRESHOLD` | `2.0` | Z-score threshold for immune anomaly detection (read via `CognitiveImmuneConfig`) |
| `MULTI_AGENT_USE_LANGGRAPH_BACKEND` | `false` | Use native LangGraph supervisor sub-graph for multi-agent dispatch (fallback to simulated backend on error) |
| `GOVERNANCE_DASHBOARD_ENABLE` | `false` | Enable FastAPI governance dashboard web UI for audit trails and compliance monitoring |
| `GOVERNANCE_DASHBOARD_HOST` | `0.0.0.0` | Host address for the governance dashboard server |
| `GOVERNANCE_DASHBOARD_PORT` | `8050` | Port for the governance dashboard server |
| `MCP_ENABLE` | `false` | Enable MCP client and dynamic tool discovery |
| `MCP_SERVERS` | `[]` | JSON array of `MCPServerConfig` objects (e.g., `[{"name":"fs","transport":"stdio","command":"npx","args":["-y","@anthropic/mcp-server-filesystem"]}`]) |
| `MCP_TIMEOUT_SECONDS` | `30` | Default timeout for MCP JSON-RPC requests |
| `BENCHMARK_ITERATIONS` | `10` | Number of measured iterations per scenario |
| `BENCHMARK_WARMUP_ITERATIONS` | `2` | Number of warmup iterations (not recorded) |
| `BENCHMARK_SCENARIOS` | `echo,safety_block,failure_recovery,context_overflow,multi_agent` | Comma-separated scenario list |
| `BENCHMARK_BASELINE_PATH` | — | Path to baseline JSON for regression detection |
| `BENCHMARK_REGRESSION_THRESHOLD_PERCENT` | `10.0` | Percentage threshold for flagging regressions |
| `BENCHMARK_OUTPUT_DIR` | `./benchmark_results` | Directory for JSON/HTML reports |
| `BENCHMARK_ENABLE_MEMORY_PROFILING` | `true` | Enable RSS/tracemalloc memory sampling |
| `BENCHMARK_ENABLE_HTML_REPORT` | `true` | Emit HTML report alongside JSON |
| `ENABLE_STREAMING` | `false` | Master switch for the real-time cognitive streaming subsystem |
| `STREAMING_TRANSPORT` | `memory` | Transport backend — `memory`, `sse`, or `websocket` |
| `STREAMING_EVENT_PERSISTENCE` | `false` | Optional event persistence — `false` or `redis` for replay |
| `STREAMING_MAX_BUFFER_EVENTS` | `1000` | Maximum events retained in the in-memory ring buffer |
| `HITL_ENABLE` | `false` | Master switch for Human-in-the-Loop gating and feedback loops |
| `HITL_DESTRUCTIVE_PATTERNS` | — | JSON array of regex strings (configurable via `HitlConfig`) |
| `HITL_TIMEOUT_SECONDS` | `300` | Timeout before pending HITL request auto-rejects |
| `HITL_AUTO_REJECT_ON_TIMEOUT` | `true` | Auto-reject pending requests on timeout |
| `HITL_ESCALATION_ON_SAFETY_VIOLATION` | `true` | Auto-escalate when safety violations exist |
| `HITL_ESCALATION_ON_IMMUNE_ALERT` | `true` | Auto-escalate when immune status is ALERT |
| `HITL_ANOMALY_THRESHOLD_FOR_ESCALATION` | `0.8` | Anomaly score that triggers escalation |
| `HITL_FEEDBACK_REPLAY_MAX_CORRECTIONS` | `5` | Max corrections to replay per turn |

All flags are env-driven and checked at config initialization time.

---

*Last updated: Post-PR #25 — Day 1 Memory Upgrade (Priority 10)*
