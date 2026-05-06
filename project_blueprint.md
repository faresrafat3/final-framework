# AIO Framework — Project Blueprint

## 1. Vision
The All-in-One Agentic Framework (AIO) is a **Cognitive Immune System / Agentic OS** built as a modular, observable, and self-correcting agent architecture. It treats every cognitive operation—from perception to action—as a layer in a resilient, anti-fragile stack.

## 2. Architecture Overview
AIO is organized into **9 layers**, implemented as a LangGraph `StateGraph` with explicit conditional routing, typed state, and layer-wise observability.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 9  │  Meta-Cognition & Self-Improvement               │
├───────────┼─────────────────────────────────────────────────┤
│  Layer 8  │  Failure Recovery & Anti-Fragility (ReCiSt)      │ Priority 1
├───────────┼─────────────────────────────────────────────────┤
│  Layer 7  │  Execution & Action (ToolGate / HermesAgent)     │ Priority 1
├───────────┼─────────────────────────────────────────────────┤
│  Layer 6  │  Tooling & Interface (MCP / Orchestra)           │
├───────────┼─────────────────────────────────────────────────┤
│  Layer 5  │  Verification & Quality Assurance (Verifier)     │ Priority 1
├───────────┼─────────────────────────────────────────────────┤
│  Layer 4  │  Reasoning & Logic (Neuro-Symbolic Engine)       │
├───────────┼─────────────────────────────────────────────────┤
│  Layer 3  │  Knowledge & World Model (Structured Ontology)   │
├───────────┼─────────────────────────────────────────────────┤
│  Layer 2  │  Dual-Memory Bridge (MemoryBridge)               │ Priority 1
├───────────┼─────────────────────────────────────────────────┤
│  Layer 1  │  Context & Attention Management (ContextManager) │ Priority 1
├───────────┼─────────────────────────────────────────────────┤
│  Layer 0  │  Infrastructure & Observability (OTel/Prom)      │ Priority 1
└───────────┴─────────────────────────────────────────────────┘
```

## 3. Priority 1 Scope
This blueprint covers the full implementation of Priority 1 layers: **0, 1, 2, 5, 7, 8**.

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

### 3.4 Layer 5 — Verification & Quality Assurance
- **LLM-as-a-Verifier**: critique generation, logical validation, evidence chains
- **FormalJudge**: deterministic rule-based checks (schema, bounds, regex, deny-lists)
- **AGEL-Comp**: competence scoring with historical trend tracking
- **AgentDebug**: self-debugging trace analysis and hypothesis generation
- Ensemble verification with configurable thresholds

### 3.5 Layer 7 — Execution & Action
- **HermesAgent**: capability-aware tool routing with registry lookup
- **Docker Sandbox**: isolated execution with resource limits, timeout enforcement, seccomp, read-only rootfs, no network
- Execution telemetry and output capture
- Safe degradation if Docker is unavailable

### 3.6 Layer 8 — Failure Recovery & Anti-Fragility
- **ReCiSt** (Recovery Circuit State Machine): states = `HEALTHY`, `DEGRADED`, `RECOVERING`, `FAILED`
- Exponential backoff with jitter for transient failures
- Escalation path for permanent failures
- Graceful degradation for catastrophic failures
- **NeuroShield**: runtime safety boundary enforcement using pattern matching + LLM classification
- Anti-fragility learning: failure mode recording and adaptive threshold tuning

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
| `verification_result` | `dict` | Verifier output (score, critiques, passed) |
| `execution_result` | `dict` | ToolGate output (stdout, stderr, exit_code) |
| `failure_state` | `str` | ReCiSt state |
| `failure_count` | `int` | Consecutive failure counter |
| `retry_budget` | `int` | Remaining retries for current operation |
| `safety_violations` | `list[dict]` | NeuroShield detected violations |
| `output` | `str | None` | Final agent output |
| `error` | `str | None` | Fatal error message |
| `metrics` | `dict` | Per-turn telemetry snapshot |

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

### 5.4 Verifier
- **Critique**: LLM-based logical validation and evidence chain construction
- **Judge**: deterministic checks (JSON schema, value bounds, regex, deny-lists)
- **Score**: AGEL-Comp competence score weighted by historical accuracy
- **Debug**: trace analysis, hypothesis generation for mismatches
- **Threshold**: configurable; default pass = ensemble score > 0.85

### 5.5 ToolGate
- **Register**: add tool metadata (name, schema, sandbox flag, timeout) to registry
- **Route**: HermesAgent selects best tool given intent + plan
- **Execute**: run in Docker sandbox with limits; capture stdout/stderr/exit code
- **Telemetry**: record latency, success/failure, resource usage

### 5.6 FailureRecovery
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

## 6. Data Flows

### 6.1 Happy Path
```
Input → Layer 1 (Ingest + Sculpt) → Layer 2 (Retrieve + Encode)
      → Layer 5 (Verify plan) → Layer 7 (Execute) → Output
```

### 6.2 Recovery Path
```
Layer 7 (Execution failure) → Layer 8 (Assess + Retry)
      → Layer 5 (Re-verify) → Layer 7 (Re-execute) → Output
```

### 6.3 Safety Violation Path
```
Any layer (Violation) → Layer 8 (NeuroShield) → Escalation / Rejection
```

### 6.4 Context Overflow Path
```
Layer 1 (Overflow) → Escalation to summary + memory consolidation
      → Truncated context + long-term retrieval
```

## 7. Graph Routing

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

## 8. SLAs & Targets

| Metric | Target | Layer |
|--------|--------|-------|
| Memory retrieval accuracy | > 90% | Layer 2 |
| Verification ensemble pass rate | > 85% | Layer 5 |
| Failure recovery rate | > 95% | Layer 8 |
| P99 execution latency | < 5s | Layer 7 |
| Context overflow handling | 100% | Layer 1 |
| Safety violation interception | 100% | Layer 8 |

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

- **Unit tests**: Mocked external dependencies; validate logic in isolation.
- **Integration tests**: Cross-layer state propagation and routing.
- **End-to-end tests**: Full graph compilation and execution with stubbed LLM.
- **Failure injection**: Chaos tests for memory corruption, tool timeout, Docker crash, boundary breach.

## 12. Security & Constitutional Mandates

1. **Orchestra of Specialists via MCP**: Every tool/interface is a specialist; no monolithic god-object.
2. **Neuro-Symbolic Mandate**: Hybrid reasoning—LLM for flexibility, formal rules for determinism.
3. **Pattern over Framework**: Reusable cognitive patterns; avoid framework lock-in.
4. **Structural Self-Critique with Skeptic**: Every layer must be verifiable by another layer; no blind trust.

---
*Blueprint version: Priority 1.0*
