# AIO Framework — All-in-One Agentic Framework

A production-grade, modular agent architecture built as a **Cognitive Immune System / Agentic OS**. AIO organizes agent cognition into 13 layers, implemented as a compiled LangGraph `StateGraph` with conditional routing, typed state, and layer-wise observability.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 12 │ Cognitive Immune System (Threat/Heal/Immunity)  │ ✅ Priority 3
├──────────┼──────────────────────────────────────────────────┤
│ Layer 11 │ Safety & Governance (Audit/Compliance/Vote)      │ ✅ Priority 3
├──────────┼──────────────────────────────────────────────────┤
│ Layer 10 │ Multi-Agent Coordination (Decompose/Dispatch)    │ ✅ Priority 3
├──────────┼──────────────────────────────────────────────────┤
│ Layer 9  │ Self-Evolution (Analyze/Report/Suggest/Apply)    │ ✅ Priority 3
├──────────┼──────────────────────────────────────────────────┤
│ Layer 8  │ Failure Recovery & Anti-Fragility (ReCiSt)       │ ✅ Priority 1
├──────────┼──────────────────────────────────────────────────┤
│ Layer 7  │ Execution & Action (ToolGate / HermesAgent)      │ ✅ Priority 1
├──────────┼──────────────────────────────────────────────────┤
│ Layer 6  │ Tool-Use Optimization (G-STEP / HDPO / JTPRO)    │ ✅ Priority 2
├──────────┼──────────────────────────────────────────────────┤
│ Layer 5  │ Verification & Quality Assurance (Verifier)      │ ✅ Priority 1
├──────────┼──────────────────────────────────────────────────┤
│ Layer 4  │ Proactive Curiosity (Novelty / Serendipity)      │ ✅ Priority 2
├──────────┼──────────────────────────────────────────────────┤
│ Layer 3  │ Planning & Anti-Myopia (HiPlan/FLARE/PPA/etc.)   │ ✅ Priority 2
├──────────┼──────────────────────────────────────────────────┤
│ Layer 2  │ Dual-Memory Bridge (MemoryBridge)                │ ✅ Priority 1
├──────────┼──────────────────────────────────────────────────┤
│ Layer 1  │ Context & Attention Management (ContextManager)  │ ✅ Priority 1
├──────────┼──────────────────────────────────────────────────┤
│ Layer 0  │ Infrastructure & Observability (OTel/Prom)       │ ✅ Priority 1
└──────────┴──────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy environment template and configure
 cp .env.example .env
# Edit .env with your keys

# 3. Run a single task
python aio_framework.py "echo hello world"

# 4. Run tests
pytest tests/ -v --cov=aio_framework

# 5. Start observability stack
docker-compose up -d
```

## Project Structure

```
.
├── aio_framework.py              # Core framework: all 13 layers + StateGraph (~2500 lines)
├── project_blueprint.md          # Full architectural specification
├── docker-compose.yml            # Observability stack (OTel, Prometheus, Grafana, Jaeger)
├── .env.example                  # Environment variable template
├── requirements.txt              # Python dependencies
├── prompts/
│   ├── system/base_system.txt    # AIO identity and operational constraints
│   ├── cognitive/recon.txt       # Reconnaissance / BAPO initialization
│   ├── cognitive/plan.txt        # Planning and task decomposition
│   ├── cognitive/prove.txt       # Proof, critique, and evidence chains
│   ├── safety/constitutional.txt # Four constitutional mandates
│   ├── safety/boundary.txt       # NeuroShield boundary protocol
│   └── meta/                     # Priority 3 meta-cognitive prompts
│       ├── self_evolution.txt    # Performance analysis and config tuning
│       ├── multi_agent.txt       # Agent registry and coordination rules
│       ├── governance.txt        # Audit checklist and voting protocol
│       └── immune.txt            # Threat scanning and auto-heal protocol
├── tests/
│   ├── unit/                     # Layer-isolated tests (10 files)
│   ├── integration/              # Cross-layer, routing, and E2E tests
│   └── failure_injection/        # Chaos and immune response tests
├── SESSION_START.md              # Session bootstrap and context recovery
├── PROJECT_STATE.md              # Completion matrix and known issues
├── DECISION_LOG.md               # Structured architectural decisions
├── CHANGELOG.md
└── README.md
```

## Key Components

- **ObservabilityLayer** (Layer 0): OpenTelemetry tracing, Prometheus metrics, structured logging, LangSmith integration.
- **ContextManager** (Layer 1): Token-aware Sculptor, BAPO attention routing, intent classification.
- **MemoryBridge** (Layer 2): Encode-verify-store-consolidate-retrieve-forget lifecycle with hybrid search.
- **PlanningLayer** (Layer 3): Hierarchical planning (HiPlan), lookahead (FLARE), pitfall avoidance (PPA), symbolic MCTS (SPIRAL), DAG decomposition (VMAO).
- **CuriosityEngine** (Layer 4): Novelty detection, information gap identification, intrinsic reward scoring.
- **Verifier** (Layer 5): Multi-modal verification ensemble (LLM critique + FormalJudge + AGEL-Comp).
- **ToolOptimizer** (Layer 6): Tool necessity scoring, policy optimization, prompt optimization (G-STEP / HDPO / JTPRO).
- **ToolGate** (Layer 7): HermesAgent routing, Docker sandbox execution, capability registry, MCP client integration for external tool discovery.
- **FailureRecovery** (Layer 8): ReCiSt state machine, NeuroShield boundaries, anti-fragility learning.
- **SelfEvolutionLayer** (Layer 9): Performance analysis, trend reporting, safe config suggestions, bounded auto-apply.
- **MultiAgentCoordinator** (Layer 10): Task decomposition, simulated dispatch/aggregate/synthesize with consensus scoring.
- **SafetyGovernance** (Layer 11): Per-turn audit trail, constitutional compliance checks, governance voting.
- **CognitiveImmuneSystem** (Layer 12): Anomaly scanning, threat detection, quarantine, auto-heal, immunity status.

## Configuration

All behavior is driven by `AIOConfig` (Pydantic v2) and environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | LLM provider key |
| `LANGCHAIN_API_KEY` | — | LangSmith tracking (optional) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OpenTelemetry collector |
| `PROMETHEUS_PORT` | `9090` | Metrics server port |
| `DOCKER_SOCKET_PATH` | `unix:///var/run/docker.sock` | Docker daemon socket |
| `MAX_RETRIES` | `3` | Failure recovery retry budget |
| `SAFETY_MODE` | `strict` | NeuroShield enforcement level |
| `ENABLE_PRIORITY_3` | `true` | Master switch for Layers 9–12 |
| `SELF_EVOLUTION_ENABLE` | `true` | Layer 9 enable |
| `MULTI_AGENT_ENABLE` | `true` | Layer 10 enable |
| `SAFETY_GOVERNANCE_ENABLE` | `true` | Layer 11 enable |
| `COGNITIVE_IMMUNE_ENABLE` | `true` | Layer 12 enable |
| `MCP_ENABLE` | `false` | Enable MCP client and dynamic tool discovery |
| `MCP_SERVERS` | `[]` | JSON array of MCP server configs |
| `MCP_TIMEOUT_SECONDS` | `30` | Timeout for MCP JSON-RPC requests |

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Failure injection / chaos
pytest tests/failure_injection/ -v

# All tests with coverage
pytest tests/ -v --cov=aio_framework --cov-report=term-missing

# Smoke tests
python -c "from aio_framework import build_aio_graph, AIOConfig; build_aio_graph(AIOConfig())"
ENABLE_PRIORITY_3=false python -c "from aio_framework import build_aio_graph, AIOConfig; build_aio_graph(AIOConfig())"
MCP_ENABLE=false python -c "from aio_framework import build_aio_graph, AIOConfig; build_aio_graph(AIOConfig())"
```

## Constitutional Mandates

1. **Orchestra of Specialists via MCP** — Every component is a bounded specialist.
2. **Neuro-Symbolic Mandate** — Hybrid reasoning: LLM + formal rules.
3. **Pattern over Framework** — Reusable, portable cognitive patterns.
4. **Structural Self-Critique** — Every layer is challengeable by another layer.

## License

MIT
