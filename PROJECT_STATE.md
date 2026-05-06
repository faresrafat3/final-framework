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
| 7 | Execution | `ToolGate` | `ToolGateConfig` | `execution_result` | `node_execute_action` | — | `test_tool_gate.py` | ✅ Complete |
| 8 | Failure Recovery | `FailureRecovery` | `FailureRecoveryConfig` | `failure_state`, `failure_count`, `retry_budget`, `safety_violations` | `node_failure_*` | `route_failure`, `route_shield` | `test_failure_recovery.py` | ✅ Complete |
| 9 | Self-Evolution | `SelfEvolutionLayer` | `SelfEvolutionConfig` | `self_evolution_report`, `performance_snapshot`, `suggested_config_delta` | `node_self_evolution_analyze` | `route_self_evolution` | `test_self_evolution.py` | ✅ Complete |
| 10 | Multi-Agent Coordination | `MultiAgentCoordinator` | `MultiAgentConfig` | `coordination_plan`, `agent_outputs`, `consensus_score` | `node_multi_agent_*` | `route_multi_agent` | `test_multi_agent.py` | ✅ Complete |
| 11 | Safety & Governance | `SafetyGovernance` | `SafetyGovernanceConfig` | `audit_trail`, `governance_result`, `compliance_violations` | `node_safety_governance_audit` | `route_safety_governance` | `test_safety_governance.py` | ✅ Complete |
| 12 | Cognitive Immune System | `CognitiveImmuneSystem` | `CognitiveImmuneConfig` | `immune_status`, `anomaly_score`, `quarantined_ids`, `healing_actions`, `threat_patterns_detected` | `node_cognitive_immune_scan` | `route_post_finalize` | `test_cognitive_immune.py` | ✅ Complete |

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

---

## 3. Known Issues / Limitations

1. **Real embedding support behind feature flag**: `sentence-transformers` integration is available via `ENABLE_REAL_EMBEDDINGS=true`. When disabled (default) or when the library is unavailable, deterministic pseudo-embeddings are used as fallback. Mixing real and pseudo vectors in the same memory store may yield inconsistent similarity scores if the flag is toggled mid-session.
2. **LangSmith requires valid API key**: Disabled automatically if unavailable.
3. **Docker sandbox requires local socket**: Falls back to graceful error if unavailable.
4. ~~Plan generation is heuristic-based~~ ✅ Done — LLM-based planning available behind `ENABLE_LLM_PLANNING` flag with graceful fallback to heuristics.
5. **Prometheus binds to all interfaces**: Configure firewall rules for production.
6. ~~Single-file growth~~ ✅ Done — `aio_framework.py` modularized into `aio/` package with `layers/`, `config/`, `graph/` submodules (see `DECISION_LOG.md`).
7. **Multi-agent dispatch is simulated**: Deterministic agent simulation using registry; no external agent framework dependencies.
8. **Self-evolution auto-apply is bounded**: Only whitelisted config keys can be modified automatically.

---

## 4. In-Flight Work

> Priority 4 is complete.

---

## 5. Ordered Next Steps (Post-Priority 4)

1. ~~Modularize `aio_framework.py`~~ ✅ Done — split into `aio/` package with `layers/`, `config/`, `graph/` submodules.
2. ~~Real embedding integration~~ ✅ Done — integrated behind `ENABLE_REAL_EMBEDDINGS` flag.
3. ~~LLM-based planning~~ ✅ Done — integrated behind `ENABLE_LLM_PLANNING` flag with optional `langchain-openai` / `langchain-anthropic` providers.
4. ~~Persistent memory backend~~ ✅ Done — `InMemoryBackend`, `RedisBackend`, `PostgresBackend`, `HybridBackend` behind `MEMORY_BACKEND_TYPE` flag.
5. ~~Cognitive immune system learning~~ ✅ Done — `ImmuneLearningEngine` with PostgreSQL storage, rolling baselines, Z-score anomaly detection behind `COGNITIVE_IMMUNE_LEARN_ENABLE` flag.
6. **Multi-agent real dispatch**: Integrate with actual agent framework (e.g., LangGraph multi-agent) behind abstraction layer.
7. **Governance dashboard**: Add web UI for audit trail and compliance monitoring.

---

## 6. Environment / Dependency Snapshot

```
Python: 3.12+
langgraph: >=0.0.50
langchain: >=0.1.0
pydantic: >=2.0
opentelemetry-api/sdk/exporter-otlp: >=1.20
prometheus-client: >=0.19
docker: >=7.0
pytest: >=8.0
pytest-asyncio: >=0.23
pytest-cov: >=4.1
sentence-transformers: >=2.2.0
redis: >=5.0.0
psycopg2-binary: >=2.9.0
langchain-openai: >=0.1.0 (optional)
langchain-anthropic: >=0.1.0 (optional)
```

**New dependencies added in Priority 4:**
- `redis>=5.0.0` (optional, behind `MEMORY_BACKEND_TYPE` / `REDIS_URL` feature flags)
- `psycopg2-binary>=2.9.0` (optional, behind `MEMORY_BACKEND_TYPE` / `POSTGRES_URL` / `COGNITIVE_IMMUNE_LEARN_ENABLE` feature flags)

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
| `COGNITIVE_IMMUNE_LEARN_ENABLE` | `false` | Enable `ImmuneLearningEngine` learned anomaly detection |
| `LEARN_ROLLING_WINDOW` | `100` | Rolling window size for immune learning baselines (read via `CognitiveImmuneConfig`) |
| `LEARN_Z_THRESHOLD` | `2.0` | Z-score threshold for immune anomaly detection (read via `CognitiveImmuneConfig`) |

All flags are env-driven and checked at config initialization time.

---

*Last updated: Priority 4 completion*
