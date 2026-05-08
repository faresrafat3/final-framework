# SESSION_START.md — AIO Framework Session Bootstrap

> **Purpose**: This document is the single source of truth for reconstructing full development context without prior chat history. Any future session should read this file first.

---

## 1. Project Identity

- **Name**: AIO Framework (All-in-One Agentic Framework)
- **Tagline**: Cognitive Immune System / Agentic OS
- **Language**: Python 3.12+
- **Core Framework**: LangGraph StateGraph
- **Architecture**: 13-layer cognitive stack (Layers 0–12)
- **Package core**: `aio/` package with `layers/`, `config/`, `graph/` submodules (`aio_framework.py` is a backward-compatible re-export shim)

---

## 2. Architecture Overview

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
│ Layer 8  │ Failure Recovery & Anti-Fragility (ReCiSt)       │ ✅ Priority 2
├──────────┼──────────────────────────────────────────────────┤
│ Layer 7  │ Execution & Action (ToolGate / HermesAgent / MCP)│ ✅ Priority 5
├──────────┼──────────────────────────────────────────────────┤
│ Layer 6  │ Tool-Use Optimization (G-STEP / HDPO / JTPRO)    │ ✅ Priority 2
├──────────┼──────────────────────────────────────────────────┤
│ Layer 5  │ Verification & Quality Assurance (Verifier)      │ ✅ Priority 2
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

---

## 3. Implementation Status Matrix

| Priority | Layers | Status | Test Coverage |
|----------|--------|--------|---------------|
| Priority 1 | 0, 1, 2, 5, 7, 8 | Complete | Unit + Integration + Chaos |
| Priority 2 | 3, 4, 6 | Complete | Unit + Integration + E2E |
| Priority 3 | 9, 10, 11, 12 | Complete | Unit + Integration + Immune |
| Priority 4 | Modularization, Persistent Memory, Immune Learning, Multi-Agent Real Dispatch, Governance Dashboard | Complete | Unit + Integration |
| Priority 5 | MCP (Model Context Protocol) Integration | Complete | Unit + Integration |
| Priority 6 | Performance Benchmark Suite | Complete | Unit + Integration |
| Priority 7 | Packaging & Distribution | Complete | CI + Smoke |
| Priority 8 | Real-Time Cognitive Streaming & Event Layer | Complete | Unit + Integration |
| Priority 9 | Human-in-the-Loop & Feedback Loop | Complete | Unit + Integration |
| Priority 10 | Memory Upgrade (4-Day: Real Embeddings, Persistent Storage, Lifecycle, Tool Exposure) | Day 1 Complete | Unit + Integration |

---

## 4. Key File Map

| File | Purpose | Approx Lines |
|------|---------|-------------|
| `aio/` | Package core: configs, state, layers, nodes, routing, graph builder | — |
| `aio/__init__.py` | Public API re-exports for clean imports | ~270 |
| `aio/state.py` | `AIOState` TypedDict and `make_initial_state()` | ~125 |
| `aio/config/models.py` | Pydantic v2 config classes (`AIOConfig`, per-layer configs) | ~155 |
| `aio/config/deps.py` | Optional dependency guards, env-driven constants | ~110 |
| `aio/layers/` | Layer implementations (14 modules) | ~1000 total |
| `aio/graph/builder.py` | `build_aio_graph()` — StateGraph assembly | ~230 |
| `aio/graph/nodes.py` | Node wrappers for every layer | ~240 |
| `aio/graph/routing.py` | Conditional edge routing functions | ~90 |
| `aio_framework.py` | Backward-compatible shim: re-exports all public symbols | ~170 |
| `project_blueprint.md` | Full 13-layer architectural spec with contracts and data flows | ~350 |
| `CHANGELOG.md` | Release notes per priority with metrics targets | ~120 |
| `README.md` | Quick start, project structure, configuration reference | ~130 |
| `SESSION_START.md` | This file — session bootstrap and context recovery | — |
| `PROJECT_STATE.md` | Persistent state: completion matrix, known issues, next steps | — |
| `DECISION_LOG.md` | Structured decision registry with rationale | — |
| `prompts/system/base_system.txt` | AIO identity and operational constraints | — |
| `prompts/cognitive/*.txt` | Recon, plan, prove prompts | 3 files |
| `prompts/safety/*.txt` | Constitutional mandates, boundary protocol | 2 files |
| `prompts/meta/*.txt` | Self-evolution, multi-agent, governance, immune prompts | 4 files |
| `tests/unit/test_*.py` | Layer-isolated unit tests (12 files) | — |
| `tests/integration/test_*.py` | Cross-layer routing and E2E tests | 4 files |
| `tests/failure_injection/test_*.py` | Chaos and immune response tests | 2 files |
| `docker-compose.yml` | Observability stack (OTel, Prometheus, Grafana, Jaeger) | — |
| `requirements.txt` | Deprecated; pointer to `pip install -e ".[dev]"` | — |
| `pyproject.toml` | PEP 621 packaging metadata, extras, console scripts | — |
| `aio/cli.py` | Unified CLI (`run`, `benchmark`, `dashboard`) | ~90 |
| `Dockerfile` | Multi-stage builder + runtime image (`python:3.12-slim`) | — |
| `.github/workflows/ci.yml` | Test matrix (3.10–3.12), build, artifact upload | — |
| `.github/workflows/publish-pypi.yml` | Trusted publishing on `v*` tags | — |
| `.github/workflows/publish-docker.yml` | Multi-arch build-push on `v*` tags | — |
| `MANIFEST.in` | sdist inclusion rules for prompts, dashboard templates, `.env.example` | — |
| `aio/benchmark/` | Benchmark suite subpackage (collector, runner, reporter, regression, CLI) | — |
| `aio/benchmark/collector.py` | `BenchmarkCollector` observability interception | ~160 |
| `aio/benchmark/runner.py` | `BenchmarkRunner` scenario execution | ~170 |
| `aio/benchmark/reporter.py` | JSON and HTML reporters | ~130 |
| `aio/benchmark/regression.py` | `RegressionDetector` baseline comparison | ~120 |
| `aio/benchmark/cli.py` | `argparse` entry point for CI | ~90 |
| `aio/streaming/` | Streaming package (events, manager, transports, store) | — |
| `tests/unit/test_streaming_*.py` | Streaming unit tests (manager, transports, store, CLI) | — |
| `docs/streaming.md` | Streaming subsystem documentation | — |
| `aio/layers/hitl.py` | HITL gate, feedback collector, escalation policy, feedback loop engine | ~200 |
| `tests/unit/test_hitl.py` | HITL gate logic, feedback ingestion, escalation thresholds, replay | — |
| `tests/integration/test_hitl_graph.py` | Graph routing with HITL enabled | — |
| `aio/dashboard/templates/hitl.html` | Dashboard HITL queue UI | — |
| `aio/memory/` | Memory subpackage: embedding engines and future storage/lifecycle modules | — |
| `aio/memory/embeddings.py` | `BaseEmbeddingEngine`, `RealEmbeddingEngine`, `PseudoEmbeddingEngine`, `EmbeddingEngineFactory` | ~120 |
| `tests/unit/test_memory_embeddings.py` | Unit tests for embedding engines (determinism, normalization, factory, dimensions) | — |

---

## 5. Build / Test / Run Commands

```bash
# Install dependencies (development mode with all extras)
pip install -e ".[dev]"

# Run full test suite
pytest tests/ -v --cov=aio --cov-report=term-missing

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/failure_injection/ -v

# Run a single task
python aio_framework.py "echo hello world"

# Start observability stack
docker-compose up -d

# Graph compilation smoke test (backward compat via shim)
python -c "from aio_framework import build_aio_graph, AIOConfig; build_aio_graph(AIOConfig())"

# Graph compilation smoke test (package import)
python -c "from aio import build_aio_graph, AIOConfig; build_aio_graph(AIOConfig())"

# Graph compilation smoke test (Priority 3 disabled)
ENABLE_PRIORITY_3=false python -c "from aio import build_aio_graph, AIOConfig; build_aio_graph(AIOConfig())"

# Run benchmark suite
python -m aio.benchmark.cli

# Run benchmark with custom scenarios
python -m aio.benchmark.cli --scenarios echo,safety_block --iterations 5

# Run benchmark tests only
pytest tests/unit/test_benchmark_collector.py tests/unit/test_benchmark_reporter.py tests/unit/test_benchmark_regression.py tests/integration/test_benchmark_suite.py -v

# CLI entry points (installed via pyproject.toml console scripts)
aio run "echo hello world"
aio benchmark
aio dashboard

# Streaming build commands
ENABLE_STREAMING=true aio run "echo hello" --stream
pytest tests/unit/test_streaming_*.py -v

# Docker build and run
docker build -t aio-framework .
docker run aio-framework run "echo hello world"

# HITL gating for destructive actions
HITL_ENABLE=true aio run "delete all files"

# HITL test suite
pytest tests/unit/test_hitl.py tests/unit/test_governance_dashboard.py tests/integration/test_hitl_graph.py -v
```

---

## 6. Session Checklist

When starting a new development session on this project, verify:

- [ ] Read `SESSION_START.md` (this file)
- [ ] Read `PROJECT_STATE.md` for current state and in-flight work
- [ ] Read `DECISION_LOG.md` for recent architectural decisions
- [ ] Run `pytest tests/ -v` to confirm baseline is green
- [ ] Check git status: `git status`
- [ ] Verify virtual environment is active
- [ ] Check `CHANGELOG.md` for recent changes

---

## 7. Recovery Protocol

If context is lost between sessions:

1. **Read the three docs**: `SESSION_START.md` → `PROJECT_STATE.md` → `DECISION_LOG.md`
2. **Run tests** to verify the codebase is in a known-good state
3. **Check git log** (`git log --oneline -10`) to see recent commits
4. **Examine any open TODOs** in the codebase: `grep -rn "TODO\|FIXME\|XXX" aio/`
5. **Review the blueprint** (`project_blueprint.md`) for the layer you intend to modify

---

## 8. Where to Start

| Goal | Start Here |
|------|-----------|
| Add a new layer | `aio/layers/` → add module → register in `aio/__init__.py` → wire into `aio/graph/builder.py` |
| Modify existing layer | Find the layer class in `aio/layers/<layer>.py`, check its unit test |
| Add tests | Mirror existing test in `tests/unit/` or `tests/integration/` |
| Update docs | `README.md`, `CHANGELOG.md`, `project_blueprint.md`, and the three session docs |
| Debug routing | `aio/graph/routing.py` + `aio/graph/builder.py` + integration tests |
| Tune safety/governance | `aio/layers/safety_governance.py` + `prompts/meta/governance.txt` |
| Tune immune system | `aio/layers/cognitive_immune.py` + `aio/layers/immune_learning.py` + `prompts/meta/immune.txt` |
| Change memory backend | `aio/layers/memory_backends.py` + `MEMORY_BACKEND_TYPE` env var |
| Change embedding engine | `aio/memory/embeddings.py` + `ENABLE_REAL_EMBEDDINGS` env var |

---

## 9. Important Conventions

- **Package core**: All layer classes live in `aio/layers/`. `aio_framework.py` is a backward-compatible re-export shim (preserves old import paths).
- **Additive only**: Never remove existing state fields from `AIOState`. Use `total=False` TypedDict.
- **Feature flags**: All new functionality is gated by env-driven flags (e.g., `ENABLE_PRIORITY_3`, `MEMORY_BACKEND_TYPE`, `COGNITIVE_IMMUNE_LEARN_ENABLE`, `MULTI_AGENT_USE_LANGGRAPH_BACKEND`, `GOVERNANCE_DASHBOARD_ENABLE`).
- **Benchmark Suite feature flags**: `BENCHMARK_ITERATIONS`, `BENCHMARK_WARMUP_ITERATIONS`, `BENCHMARK_SCENARIOS`, `BENCHMARK_BASELINE_PATH`, `BENCHMARK_REGRESSION_THRESHOLD_PERCENT`, `BENCHMARK_OUTPUT_DIR`, `BENCHMARK_ENABLE_MEMORY_PROFILING`, `BENCHMARK_ENABLE_HTML_REPORT`.
- **Streaming feature flags**: `ENABLE_STREAMING`, `STREAMING_TRANSPORT`, `STREAMING_EVENT_PERSISTENCE`, `STREAMING_MAX_BUFFER_EVENTS`.
- **HITL feature flags**: `HITL_ENABLE`, `HITL_DESTRUCTIVE_PATTERNS`, `HITL_TIMEOUT_SECONDS`, `HITL_AUTO_REJECT_ON_TIMEOUT`, `HITL_ESCALATION_ON_SAFETY_VIOLATION`, `HITL_ESCALATION_ON_IMMUNE_ALERT`, `HITL_ANOMALY_THRESHOLD_FOR_ESCALATION`, `HITL_FEEDBACK_REPLAY_MAX_CORRECTIONS`.
- **Observability**: Every layer method wraps logic in `self.obs.start_span()` and calls `record_latency()` + `count_node()`.
- **Graceful degradation**: All external dependencies are optional with feature flags (`OTEL_AVAILABLE`, `REDIS_AVAILABLE`, `PSYCOPG2_AVAILABLE`, `HTTPX_AVAILABLE`, etc.).
- **No new required dependencies**: Priority 4 added `redis>=5.0.0` and `psycopg2-binary>=2.9.0` to `requirements.txt`, but both are optional at runtime (guarded by availability checks and feature flags). Priority 5 uses existing `httpx>=0.25.0` for MCP SSE transport.
- **Benchmark optional dependencies**: `psutil` enables RSS memory profiling in `BenchmarkCollector`; `jinja2` enables rich HTML templating in `HTMLReporter`. Both are runtime-guarded (`PSUTIL_AVAILABLE`, `JINJA2_AVAILABLE`) with graceful fallback to `tracemalloc` and plain HTML respectively.
- **`pyproject.toml` is the single source of truth for dependencies**; `requirements.txt` is deprecated (pointer only).
- **Optional features are installable as extras**: `dashboard`, `llm`, `embeddings`, `memory-redis`, `memory-postgres`, `benchmark`, `dev`, `all`.
- **Console entry points** `aio` and `aio-benchmark` are defined in `pyproject.toml` `[project.scripts]`.

---

*Last updated: Post-PR #25 — Day 1 Memory Upgrade (Priority 10)*
