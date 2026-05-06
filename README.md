# AIO Framework — All-in-One Agentic Framework (Priority 1)

A production-grade, modular agent architecture built as a **Cognitive Immune System / Agentic OS**. AIO organizes agent cognition into 9 layers, with Priority 1 implementing Layers 0, 1, 2, 5, 7, and 8 as a compiled LangGraph `StateGraph`.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 9  │  Meta-Cognition & Self-Improvement               │
├───────────┼─────────────────────────────────────────────────┤
│  Layer 8  │  Failure Recovery & Anti-Fragility (ReCiSt)      │ ✅ Priority 1
├───────────┼─────────────────────────────────────────────────┤
│  Layer 7  │  Execution & Action (ToolGate / HermesAgent)     │ ✅ Priority 1
├───────────┼─────────────────────────────────────────────────┤
│  Layer 6  │  Tooling & Interface (MCP / Orchestra)           │
├───────────┼─────────────────────────────────────────────────┤
│  Layer 5  │  Verification & Quality Assurance (Verifier)     │ ✅ Priority 1
├───────────┼─────────────────────────────────────────────────┤
│  Layer 4  │  Reasoning & Logic (Neuro-Symbolic Engine)       │
├───────────┼─────────────────────────────────────────────────┤
│  Layer 3  │  Knowledge & World Model (Structured Ontology)   │
├───────────┼─────────────────────────────────────────────────┤
│  Layer 2  │  Dual-Memory Bridge (MemoryBridge)               │ ✅ Priority 1
├───────────┼─────────────────────────────────────────────────┤
│  Layer 1  │  Context & Attention Management (ContextManager) │ ✅ Priority 1
├───────────┼─────────────────────────────────────────────────┤
│  Layer 0  │  Infrastructure & Observability (OTel/Prom)      │ ✅ Priority 1
└───────────┴─────────────────────────────────────────────────┘
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
├── aio_framework.py              # Core framework: all Priority 1 layers + StateGraph
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
│   └── safety/boundary.txt       # NeuroShield boundary protocol
├── tests/
│   ├── unit/                     # Layer-isolated tests
│   ├── integration/              # Cross-layer and end-to-end tests
│   └── failure_injection/        # Chaos and resilience tests
├── CHANGELOG.md
└── README.md
```

## Key Components

- **ObservabilityLayer** (Layer 0): OpenTelemetry tracing, Prometheus metrics, structured logging, LangSmith integration.
- **ContextManager** (Layer 1): Token-aware Sculptor, BAPO attention routing, intent classification.
- **MemoryBridge** (Layer 2): Encode-verify-store-consolidate-retrieve-forget lifecycle with hybrid search.
- **Verifier** (Layer 5): Multi-modal verification ensemble (LLM critique + FormalJudge + AGEL-Comp).
- **ToolGate** (Layer 7): HermesAgent routing, Docker sandbox execution, capability registry.
- **FailureRecovery** (Layer 8): ReCiSt state machine, NeuroShield boundaries, anti-fragility learning.

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
```

## Constitutional Mandates

1. **Orchestra of Specialists via MCP** — Every component is a bounded specialist.
2. **Neuro-Symbolic Mandate** — Hybrid reasoning: LLM + formal rules.
3. **Pattern over Framework** — Reusable, portable cognitive patterns.
4. **Structural Self-Critique** — Every layer is challengeable by another layer.

## License

MIT
