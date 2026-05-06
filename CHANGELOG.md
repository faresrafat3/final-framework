# Changelog

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
- Plan generation is heuristic-based; full LLM-based planning deferred to Priority 2.
- Prometheus HTTP server binds to all interfaces; configure firewall rules for production.
