# AGENTS.md — AIO Framework Project Context

## Build, Test, and Verification Commands
- Install: `pip install -e ".[dev]"`
- Run all tests: `python -m pytest tests/ -v`
- Run a single test: `python -m pytest tests/unit/test_memory_v2.py -v`
- Type checking: `python -m mypy aio/`
- Lint: `python -m ruff check aio/`
- Done-when: ALL tests pass with `pytest tests/unit/test_memory_v2.py -v`

## Repository Layout
- `aio/` — Core framework package
  - `aio/memory/` — Memory subsystem (bridge.py, embeddings.py, backends.py, lifecycle.py)
  - `aio/graph/` — LangGraph StateGraph assembly
  - `aio/layers/` — All 13 cognitive layers
  - `aio/config/` — Configuration (Pydantic v2)
  - `aio/tools/` — Tool registration and execution
- `tests/` — Test suite (unit/, integration/, failure_injection/)
- `prompts/` — Prompt templates (system/, cognitive/, safety/)

## Architectural Rules (Non-Negotiable)
1. **Memory is a Full Operating System** — The MemoryBridge MUST implement
   the full lifecycle: ENCODE → VERIFY → STORE → CONSOLIDATE → RETRIEVE → FORGET.
2. **Real Embeddings** — Use `sentence-transformers/all-MiniLM-L6-v2`
   for embeddings. NEVER use hashlib pseudo-vectors in production.
3. **Persistent Storage** — Use PostgreSQL + pgvector for production.
   Fall back to in-memory dict ONLY when PG is unavailable.
4. **All components are optional and swappable** — Every new component
   must be behind a feature flag (e.g., `ENABLE_REAL_EMBEDDINGS`, `ENABLE_POSTGRES`).

## Forbidden Actions
- Do NOT generate placeholder comments or empty stubs.
- Do NOT simulate memory — use real embeddings and real SQL.
- Do NOT modify existing tests without explicit approval.
- Do NOT delete or alter existing core files unless explicitly instructed.
