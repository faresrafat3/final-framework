# AIO Framework — Project Blueprint

## 1. Vision
The All-in-One Agentic Framework (AIO) is a **Cognitive Immune System / Agentic OS** built as a modular, observable, and self-correcting agent architecture. It treats every cognitive operation—from perception to action—as a layer in a resilient, anti-fragile stack.

## 2. Architecture Overview
AIO is organized into **13 layers**, implemented as a LangGraph `StateGraph` with explicit conditional routing, typed state, and layer-wise observability.

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 12 │ Cognitive Immune System (Threat/Heal/Immunity)  │ Priority 3
├──────────┼──────────────────────────────────────────────────┤
│ Layer 11 │ Safety & Governance (Audit/Compliance/Vote)      │ Priority 3
├──────────┼──────────────────────────────────────────────────┤
│ Layer 10 │ Multi-Agent Coordination (Decompose/Dispatch)    │ Priority 3
├──────────┼──────────────────────────────────────────────────┤
│ Layer 9  │ Self-Evolution (Analyze/Report/Suggest/Apply)    │ Priority 3
├──────────┼──────────────────────────────────────────────────┤
│ Layer 8  │ Failure Recovery & Anti-Fragility (ReCiSt)       │ Priority 1
├──────────┼──────────────────────────────────────────────────┤
│ Layer 7  │ Execution & Action (ToolGate / HermesAgent)      │ Priority 1
├──────────┼──────────────────────────────────────────────────┤
│ Layer 6  │ Tool-Use Optimization (G-STEP / HDPO / JTPRO)    │ Priority 2
├──────────┼──────────────────────────────────────────────────┤
│ Layer 5  │ Verification & Quality Assurance (Verifier)      │ Priority 1
├──────────┼──────────────────────────────────────────────────┤
│ Layer 4  │ Proactive Curiosity (Novelty / Serendipity)      │ Priority 2
├──────────┼──────────────────────────────────────────────────┤
│ Layer 3  │ Planning & Anti-Myopia (HiPlan/FLARE/PPA/etc.)   │ Priority 2
├──────────┼──────────────────────────────────────────────────┤
│ Layer 2  │ Dual-Memory Bridge (MemoryBridge)                │ Priority 1
├──────────┼──────────────────────────────────────────────────┤
│ Layer 1  │ Context & Attention Management (ContextManager)  │ Priority 1
├──────────┼──────────────────────────────────────────────────┤
│ Layer 0  │ Infrastructure & Observability (OTel/Prom)       │ Priority 1
└──────────┴──────────────────────────────────────────────────┘
```

## 3. Layer Specifications

### 3.1 Layer 0 — Infrastructure & Observability
- **OpenTelemetry** tracing and metrics with OTLP export
- **Prometheus** client metrics exposed via HTTP
- **LangSmith** run tracking (optional, graceful degradation)
- Structured JSON logging with correlation IDs
- Health check endpoint

### 3.2 Layer 1 — Context & Attention Management
- **Sculptor**: token-aware context window management with approximate counting
- **BAPO** (Base-Attention-Priority-Oracle): dynamic attention routing based on intent, urgency, and resource availability
- Working memory pruning with importance and recency weighting
- Context overflow detection and escalation

### 3.3 Layer 2 — Dual-Memory Bridge
- **Hindsight**: episodic memory for recent interactions
- **MemForge**: memory consolidation from working to long-term
- **SynapticAI**: associative retrieval using hybrid vector + keyword search
- **ElephantBroker**: long-term storage broker (pluggable backend)
- **MIA** (Memory Importance Assessment): scoring for retention and recall priority
- Full lifecycle: encode → verify → store → consolidate → retrieve → forget

### 3.4 Layer 3 — Planning & Anti-Myopia
- **HiPlan**: hierarchical task decomposition with configurable max depth
- **FLARE**: lookahead planning with horizon window
- **PPA**: pitfall pattern analysis before execution
- **SPIRAL**: symbolic MCTS with configurable simulations
- **VMAO**: DAG-based plan decomposition with replanning

### 3.5 Layer 4 — Proactive Curiosity
- Novelty detection with configurable threshold
- Information gap tracking
- Intrinsic reward scoring for exploration

### 3.6 Layer 5 — Verification & Quality Assurance
- **LLM-as-a-Verifier**: critique generation, logical validation, evidence chains
- **FormalJudge**: deterministic rule-based checks (schema, bounds, regex, deny-lists)
- **AGEL-Comp**: competence scoring with historical trend tracking
- **AgentDebug**: self-debugging trace analysis and hypothesis generation
- Ensemble verification with configurable thresholds

### 3.7 Layer 6 — Tool-Use Optimization
- **G-STEP**: tool necessity scoring with configurable threshold
- **HDPO**: accuracy/efficiency weighted policy optimization
- **JTPRO**: iterative prompt optimization
- Tool analytics tracking for deprecation decisions

### 3.8 Layer 7 — Execution & Action
- **HermesAgent**: capability-aware tool routing with registry lookup
- **Docker Sandbox**: isolated execution with resource limits, timeout enforcement, seccomp, read-only rootfs, no network
- Execution telemetry and output capture
- Safe degradation if Docker is unavailable

### 3.9 Layer 8 — Failure Recovery & Anti-Fragility
- **ReCiSt** (Recovery Circuit State Machine): states = `HEALTHY`, `DEGRADED`, `RECOVERING`, `FAILED`
- Exponential backoff with jitter for transient failures
- Escalation path for permanent failures
- Graceful degradation for catastrophic failures
- **NeuroShield**: runtime safety boundary enforcement using pattern matching + LLM classification
- Anti-fragility learning: failure mode recording and adaptive threshold tuning

### 3.10 Layer 9 — Self-Evolution
- Performance snapshot recording per turn
- Trend reporting over a configurable sliding window
- Safe config delta suggestions with bounded auto-apply whitelist
- Post-finalize reflection pipeline

### 3.11 Layer 10 — Multi-Agent Coordination
- Task decomposition by intent (`coding`, `analysis`, `general`)
- Simulated agent dispatch/aggregate/synthesize using a configurable registry
- Consensus scoring based on output variance across simulated agents

### 3.12 Layer 11 — Safety & Governance
- Per-turn audit trail recording
- Constitutional compliance checks against four mandates
- Governance voting with configurable thresholds for sensitive operations

### 3.13 Layer 12 — Cognitive Immune System
- Anomaly scanning (failure rate, corrupted memory, threat patterns)
- Quarantine system: copies suspicious entries without destructive deletion
- Auto-heal with TTL-based threat pattern pruning
- Immunity status tracking (`HEALTHY`, `ALERT`, `COMPROMISED`)

## 4. State Schema (`AIOState`)
The LangGraph state is a `TypedDict` with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `str` | Unique session identifier |
| `trace_id` | `str` | OpenTelemetry trace ID |
| `turn` | `int` | Interaction turn counter |
| `raw_input` | `str` | User / environment input |
| `intent` | `str | None` | Classified intent |
| `context_window` | `list[dict]` | Active context tokens/messages |
| `context_budget` | `int` | Remaining token budget |
| `attention_map` | `dict[str, float]` | BAPO attention scores per layer |
| `working_memory` | `list[dict]` | Short-term memory buffer |
| `long_term_memory` | `list[dict]` | Consolidated memory entries |
| `memory_confidence` | `float` | Retrieval confidence [0,1] |
| `plan` | `str | None` | Generated plan / strategy |
| `hierarchical_plan` | `dict | None` | HiPlan decomposition tree |
| `lookahead_result` | `dict | None` | FLARE horizon results |
| `fact_augmented_plan` | `str | None` | PPA-augmented plan |
| `pitfall_analysis` | `dict | None` | PPA detected risks |
| `spiral_tree` | `dict | None` | SPIRAL MCTS tree |
| `mars_reflection` | `str | None` | Meta-reflection output |
| `maci_meta_plan` | `str | None` | Meta-planner selection |
| `vmao_dag` | `list[dict] | None` | VMAO task DAG |
| `curiosity_score` | `float` | Current curiosity activation |
| `novelty_map` | `dict[str, float]` | Per-concept novelty scores |
| `information_gaps` | `list[str]` | Detected knowledge gaps |
| `verification_result` | `dict` | Verifier output (score, critiques, passed) |
| `tool_necessity_score` | `float` | G-STEP necessity score |
| `tool_policy_channels` | `dict` | HDPO optimized policies |
| `tool_prompt_optimization` | `dict` | JTPRO prompt improvements |
| `sandbox_result` | `dict | None` | Sandbox execution result |
| `tool_analytics` | `dict` | Per-tool usage analytics |
| `execution_result` | `dict` | ToolGate output (stdout, stderr, exit_code) |
| `failure_state` | `str` | ReCiSt state |
| `failure_count` | `int` | Consecutive failure counter |
| `retry_budget` | `int` | Remaining retries for current operation |
| `safety_violations` | `list[dict]` | NeuroShield detected violations |
| `output` | `str | None` | Final agent output |
| `error` | `str | None` | Fatal error message |
| `metrics` | `dict` | Per-turn telemetry snapshot |
| `self_evolution_report` | `dict | None` | Layer 9 performance report |
| `performance_snapshot` | `dict | None` | Layer 9 per-turn snapshot |
| `suggested_config_delta` | `list[dict] | None` | Layer 9 proposed changes |
| `coordination_plan` | `dict | None` | Layer 10 multi-agent plan |
| `agent_outputs` | `dict | None` | Layer 10 simulated outputs |
| `consensus_score` | `float | None` | Layer 10 consensus metric |
| `audit_trail` | `list[dict] | None` | Layer 11 audit entries |
| `governance_result` | `dict | None` | Layer 11 vote outcome |
| `compliance_violations` | `list[dict] | None` | Layer 11 violations found |
| `immune_status` | `str | None` | Layer 12 status (`HEALTHY`/`ALERT`/`COMPROMISED`) |
| `anomaly_score` | `float | None` | Layer 12 anomaly metric |
| `quarantined_ids` | `list[str] | None` | Layer 12 quarantined entry IDs |
| `healing_actions` | `list[dict] | None` | Layer 12 heal attempts |
| `threat_patterns_detected` | `list[dict] | None` | Layer 12 threat patterns |

## 5. Component Contracts

### 5.1 ObservabilityLayer
- **Initialize**: configure tracer provider, meters, log handler
- **Start span**: create OTel span with baggage / context propagation
- **Record metric**: increment counters, observe histograms, set gauges
- **Export**: flush to OTLP endpoint; fallback to stdout if unreachable

### 5.2 ContextManager
- **Ingest**: accept raw input, classify intent, initialize attention map
- **Sculpt**: trim context_window to fit budget; prefer recency + importance
- **Route**: return next layer based on BAPO scores (`memory`, `verify`, `execute`, `recover`)

### 5.3 MemoryBridge
- **Encode**: embed input + metadata; assign MIA importance score
- **Verify**: run verification gate before storage (schema, dedup)
- **Store**: write to Hindsight (episodic); schedule MemForge consolidation
- **Consolidate**: batch-merge episodic entries into long-term via ElephantBroker
- **Retrieve**: hybrid search over Hindsight + long-term; return top-k with confidence
- **Forget**: prune entries below importance threshold or exceeding TTL

### 5.4 PlanningLayer
- **HiPlan**: decompose task into hierarchical sub-tasks with depth limit
- **FLARE**: simulate future steps to detect dead-ends early
- **PPA**: analyze plan for known pitfalls and augment with mitigations
- **SPIRAL**: run symbolic MCTS to optimize plan branches
- **VMAO**: build DAG dependency graph; detect cycles; replan if needed

### 5.5 CuriosityEngine
- **Detect novelty**: compare input against novelty map; flag if below threshold
- **Track gaps**: record information gaps for future exploration
- **Score reward**: compute intrinsic reward for exploration vs exploitation

### 5.6 Verifier
- **Critique**: LLM-based logical validation and evidence chain construction
- **Judge**: deterministic checks (JSON schema, value bounds, regex, deny-lists)
- **Score**: AGEL-Comp competence score weighted by historical accuracy
- **Debug**: trace analysis, hypothesis generation for mismatches
- **Threshold**: configurable; default pass = ensemble score > 0.85

### 5.7 ToolOptimizer
- **G-STEP**: score whether a tool is necessary for the current task
- **HDPO**: optimize policy weights balancing accuracy vs efficiency
- **JTPRO**: iteratively refine tool prompts to improve success rate
- **Analytics**: track tool usage for deprecation decisions

### 5.8 ToolGate
- **Register**: add tool metadata (name, schema, sandbox flag, timeout) to registry
- **Route**: HermesAgent selects best tool given intent + plan
- **Execute**: run in Docker sandbox with limits; capture stdout/stderr/exit code
- **Telemetry**: record latency, success/failure, resource usage

### 5.9 FailureRecovery
- **Assess**: classify failure (transient / permanent / catastrophic)
- **Act**: exponential backoff, retry, escalate, or degrade
- **Shield**: NeuroShield intercepts safety violations; logs + blocks + escalates
- **Learn**: record failure mode, update adaptive thresholds, tune retry budgets
- **State machine transitions**:
  - `HEALTHY` → `DEGRADED` (first failure)
  - `DEGRADED` → `RECOVERING` (retry initiated)
  - `RECOVERING` → `HEALTHY` (retry success)
  - `RECOVERING` → `FAILED` (retry exhaustion)
  - `FAILED` → `HEALTHY` (manual reset or anti-fragile recovery)

### 5.10 SelfEvolutionLayer
- **Analyze**: record performance snapshot (latency, errors, memory quality)
- **Report**: generate trend report over sliding window
- **Suggest**: propose config deltas based on detected trends
- **Apply**: auto-apply only whitelisted tunable keys; log all changes

### 5.11 MultiAgentCoordinator
- **Decompose**: split task into sub-tasks based on intent classification
- **Dispatch**: send sub-tasks to simulated agents from registry
- **Aggregate**: collect outputs; compute consensus score from variance
- **Synthesize**: merge results into unified plan or response

### 5.12 SafetyGovernance
- **Audit**: record per-turn audit trail with timestamp and layer context
- **Compliance**: check against constitutional mandates; flag violations
- **Vote**: run governance vote for sensitive operations; block if threshold not met
- **Record**: append decision to audit trail for accountability

### 5.13 CognitiveImmuneSystem
- **Scan**: inspect state for anomalies (failure rate, memory corruption, patterns)
- **Detect**: classify threats; increment counters; update threat DB
- **Quarantine**: copy suspicious entries to quarantine store without deletion
- **Heal**: attempt remediation; clear quarantine on success; log actions
- **Update immunity**: set status (`HEALTHY`, `ALERT`, `COMPROMISED`) based on scan

## 6. Data Flows

### 6.1 Happy Path
```
Input → Layer 1 (Ingest + Sculpt) → Layer 2 (Retrieve + Encode)
      → Layer 3 (Plan) → Layer 5 (Verify plan)
      → Layer 6 (Optimize) → Layer 7 (Execute) → Output
```

### 6.2 Multi-Agent Branch (coding/analysis intents)
```
Layer 1 (Intent = coding|analysis) → Layer 10 (Decompose + Dispatch)
      → Layer 10 (Aggregate + Synthesize) → Layer 3 (Plan) → ...
```

### 6.3 Recovery Path
```
Layer 7 (Execution failure) → Layer 8 (Assess + Retry)
      → Layer 5 (Re-verify) → Layer 7 (Re-execute) → Output
```

### 6.4 Safety Violation Path
```
Any layer (Violation) → Layer 8 (NeuroShield) → Escalation / Rejection
```

### 6.5 Governance Audit Gate
```
Layer 3 (Plan) → Layer 11 (Audit + Compliance) → Layer 5 (Verify)
      → (Blocked if governance vote fails)
```

### 6.6 Post-Finalize Reflection
```
Layer 7 (Output finalized) → Layer 9 (Analyze + Report)
      → Layer 11 (Governance record) → Layer 12 (Scan + Heal)
```

### 6.7 Context Overflow Path
```
Layer 1 (Overflow) → Escalation to summary + memory consolidation
      → Truncated context + long-term retrieval
```

## 7. Graph Routing

### Priority 1/2 Core Routing

| Source Node | Condition | Target Node |
|-------------|-----------|-------------|
| `context_ingest` | default | `memory_retrieve` |
| `memory_retrieve` | `memory_confidence < 0.7` | `memory_encode` |
| `memory_retrieve` | `memory_confidence >= 0.7` | `plan_generate` |
| `plan_generate` | default | `verify_plan` |
| `verify_plan` | `verification_result["passed"]` | `execute_action` |
| `verify_plan` | `!verification_result["passed"]` | `debug_and_replan` |
| `execute_action` | `execution_result["success"]` | `finalize_output` |
| `execute_action` | `!execution_result["success"]` | `failure_assess` |
| `failure_assess` | `transient` | `retry_with_backoff` |
| `failure_assess` | `permanent` | `escalate` |
| `failure_assess` | `catastrophic` | `graceful_degrade` |
| `retry_with_backoff` | default | `verify_plan` |
| `debug_and_replan` | default | `plan_generate` |
| `escalate` | default | `finalize_output` (with error) |
| `graceful_degrade` | default | `finalize_output` (with degraded output) |

### Priority 3 Conditional Routing (when `ENABLE_PRIORITY_3=true`)

| Source Node | Condition | Target Node |
|-------------|-----------|-------------|
| `context_ingest` | `intent in ("coding", "analysis")` | `multi_agent_decompose` |
| `context_ingest` | `intent not in ("coding", "analysis")` | `memory_retrieve` |
| `multi_agent_synthesize` | default | `memory_retrieve` |
| `vmao_decompose` | default | `safety_governance_audit` |
| `safety_governance_audit` | `governance_result["approved"]` | `verify_plan` |
| `safety_governance_audit` | `!governance_result["approved"]` | `escalate` |
| `finalize_output` | `enable_priority_3` | `self_evolution_analyze` |
| `self_evolution_analyze` | `enable_priority_3` | `cognitive_immune_scan` |
| `cognitive_immune_scan` | default | `END` |

## 8. SLAs & Targets

| Metric | Target | Layer |
|--------|--------|-------|
| Memory retrieval accuracy | > 90% | Layer 2 |
| Verification ensemble pass rate | > 85% | Layer 5 |
| Failure recovery rate | > 95% | Layer 8 |
| P99 execution latency | < 5s | Layer 7 |
| Context overflow handling | 100% | Layer 1 |
| Safety violation interception | 100% | Layer 8 |
| Governance audit coverage | 100% | Layer 11 |
| Immune false positive rate | < 5% | Layer 12 |
| Self-evolution backward compat | 100% | Layer 9 |

## 9. Integration Patterns

- **LangGraph**: All layers compile into a single `StateGraph` with conditional edges.
- **Pydantic v2**: Configuration and state boundary validation.
- **OpenTelemetry**: Trace every node execution; propagate trace IDs through state.
- **Prometheus**: Expose counters/histograms for node latency, routing decisions, failure rates.
- **Docker SDK**: Sandbox execution with `docker-py`.
- **LangSmith**: Optional run tracking; disabled if `LANGCHAIN_API_KEY` is unset.

## 10. Deployment

- **docker-compose.yml**: OTel Collector, Prometheus, Grafana, Jaeger, framework service.
- **Environment**: `.env` drives all configuration; `.env.example` documents every variable.
- **Health**: `/health` endpoint checks graph compilation and dependency connectivity.

## 11. Testing Strategy

- **Unit tests**: Mocked external dependencies; validate logic in isolation (10 files, 60+ tests).
- **Integration tests**: Cross-layer state propagation and routing (3 files, 20+ tests).
- **End-to-end tests**: Full graph compilation and execution with stubbed LLM.
- **Failure injection**: Chaos tests for memory corruption, tool timeout, Docker crash, boundary breach, immune response.

## 12. Security & Constitutional Mandates

1. **Orchestra of Specialists via MCP**: Every tool/interface is a specialist; no monolithic god-object.
2. **Neuro-Symbolic Mandate**: Hybrid reasoning—LLM for flexibility, formal rules for determinism.
3. **Pattern over Framework**: Reusable cognitive patterns; avoid framework lock-in.
4. **Structural Self-Critique with Skeptic**: Every layer must be verifiable by another layer; no blind trust.

## 13. Session Continuity

Three documents provide persistent context across sessions:

- **`SESSION_START.md`**: Bootstrap guide, architecture overview, file map, build commands, recovery protocol.
- **`PROJECT_STATE.md`**: Layer completion matrix, test coverage matrix, known issues, in-flight work, next steps.
- **`DECISION_LOG.md`**: Structured decision registry with context, consequences, and status.

---
*Blueprint version: Priority 3.0*
