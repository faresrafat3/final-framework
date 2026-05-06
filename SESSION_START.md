# SESSION_START.md — AIO Framework Session Bootstrap

> **Purpose**: This document is the single source of truth for reconstructing full development context without prior chat history. Any future session should read this file first.

---

## 1. Project Identity

- **Name**: AIO Framework (All-in-One Agentic Framework)
- **Tagline**: Cognitive Immune System / Agentic OS
- **Language**: Python 3.12+
- **Core Framework**: LangGraph StateGraph
- **Architecture**: 13-layer cognitive stack (Layers 0–12)
- **Single-file core**: `aio_framework.py` (~2600 lines)

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
│ Layer 7  │ Execution & Action (ToolGate / HermesAgent)      │ ✅ Priority 2
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

---

## 4. Key File Map

| File | Purpose | Approx Lines |
|------|---------|-------------|
| `aio_framework.py` | Single-file core: all configs, state, layers, nodes, routing, graph builder | ~2600 |
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
| `tests/unit/test_*.py` | Layer-isolated unit tests (10 files) | — |
| `tests/integration/test_*.py` | Cross-layer routing and E2E tests | 3 files |
| `tests/failure_injection/test_*.py` | Chaos and immune response tests | 2 files |
| `docker-compose.yml` | Observability stack (OTel, Prometheus, Grafana, Jaeger) | — |
| `requirements.txt` | Python dependencies (no new deps for Priority 3) | ~10 packages |

---

## 5. Build / Test / Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run full test suite
pytest tests/ -v --cov=aio_framework --cov-report=term-missing

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/failure_injection/ -v

# Run a single task
python aio_framework.py "echo hello world"

# Start observability stack
docker-compose up -d

# Graph compilation smoke test (backward compat)
python -c "from aio_framework import build_aio_graph, AIOConfig; build_aio_graph(AIOConfig())"

# Graph compilation smoke test (Priority 3 enabled)
ENABLE_PRIORITY_3=true python -c "from aio_framework import build_aio_graph, AIOConfig; build_aio_graph(AIOConfig())"
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
4. **Examine any open TODOs** in the codebase: `grep -rn "TODO\|FIXME\|XXX" aio_framework.py`
5. **Review the blueprint** (`project_blueprint.md`) for the layer you intend to modify

---

## 8. Where to Start

| Goal | Start Here |
|------|-----------|
| Add a new layer | `aio_framework.py` → Config → State → Layer class → Node wrapper → Routing → Graph builder |
| Modify existing layer | Find the layer class in `aio_framework.py`, check its unit test |
| Add tests | Mirror existing test in `tests/unit/` or `tests/integration/` |
| Update docs | `README.md`, `CHANGELOG.md`, `project_blueprint.md`, and the three session docs |
| Debug routing | `build_aio_graph()` in `aio_framework.py` + integration tests |
| Tune safety/governance | Layer 11 (`SafetyGovernance`) + `prompts/meta/governance.txt` |
| Tune immune system | Layer 12 (`CognitiveImmuneSystem`) + `prompts/meta/immune.txt` |

---

## 9. Important Conventions

- **Single-file core**: All layer classes live in `aio_framework.py`. Future modularization is documented in `DECISION_LOG.md`.
- **Additive only**: Never remove existing state fields from `AIOState`. Use `total=False` TypedDict.
- **Feature flags**: All new functionality is gated by env-driven flags (e.g., `ENABLE_PRIORITY_3`).
- **Observability**: Every layer method wraps logic in `self.obs.start_span()` and calls `record_latency()` + `count_node()`.
- **Graceful degradation**: All external dependencies are optional with feature flags (`OTEL_AVAILABLE`, etc.).
- **No new dependencies**: Priority 3 added zero new Python packages.

---

*Last updated: Priority 3 completion*
