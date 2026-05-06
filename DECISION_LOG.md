# DECISION_LOG.md — Structured Decision Registry

> **Purpose**: Capture significant architectural and implementation decisions with context, consequences, and status. Future sessions should review recent entries before making changes.

---

## Format

| ID | Date | Decision | Context | Consequences | Status |
|----|------|----------|---------|--------------|--------|

---

## Decisions

| D001 | 2024-05-05 | Single-file core architecture (`aio_framework.py`) | Simplifies imports, ensures atomic consistency, reduces packaging overhead | File grows large (~2600 lines after Priority 3); future modularization may be needed | Active |
| D002 | 2024-05-05 | Pydantic v2 for all configuration | Strong typing, validation, env var integration | Requires `pydantic>=2.0`; breaks compatibility with v1 | Active |
| D003 | 2024-05-05 | TypedDict with `total=False` for state | Allows additive fields without breaking existing code | Less strict than dataclass; typos in field names silently ignored | Active |
| D004 | 2024-05-05 | All external dependencies optional with feature flags | Enables standalone testing, reduces environment drift | Code must check flags before every external call | Active |
| D005 | 2024-05-05 | Deterministic pseudo-embeddings for memory | No external model dependency for standalone operation | Retrieval accuracy lower than real embeddings | Active |
| D006 | 2024-05-05 | Docker sandbox as default execution mode | Strong isolation, resource limits, read-only rootfs | Requires Docker socket; falls back to error gracefully | Active |
| D007 | 2024-05-06 | Implement Priority 3 (Layers 9-12) additively with zero breaking changes | Preserve all Priority 1/2 tests and graph behavior | Increased graph complexity; more conditional edges to maintain | Active |
| D008 | 2024-05-06 | Master feature flag `enable_priority_3` with per-layer sub-flags | Allows gradual rollout and individual layer disable | More config surface area; all routing functions must check flags | Active |
| D009 | 2024-05-06 | Post-finalize reflection pipeline for Layers 9, 11, 12 | Self-evolution and immune system run after output finalization | Adds latency to every turn when enabled; mitigated by lightweight operations | Active |
| D010 | 2024-05-06 | Multi-agent coordination integrates before planning as optional branch | Complex tasks get decomposed across simulated agents | Agent dispatch is simulated, not real; future work to integrate actual agents | Active |
| D011 | 2024-05-06 | Safety governance audit gate runs before verification | Adds constitutional compliance check to planning pipeline | May block valid plans if compliance is overly strict; threshold is configurable | Active |
| D012 | 2024-05-06 | Immune system quarantine copies but does not delete until heal() | Prevents data loss from false positives | Quarantine store grows until heal() runs; mitigated by TTL | Active |
| D013 | 2024-05-06 | Self-evolution auto-apply whitelists only bounded config keys | Prevents safety threshold or layer disable from automatic changes | Only `retrieval_top_k`, backoff timing, and similar tunables can auto-apply | Active |
| D014 | 2024-05-06 | No new Python dependencies for Priority 3 | Minimizes environment drift, keeps `requirements.txt` stable | Simulated multi-agent dispatch instead of real agent framework | Active |
| D015 | 2024-05-06 | Create SESSION_START.md, PROJECT_STATE.md, DECISION_LOG.md | Prevents context loss between development sessions | Three additional files to maintain; updates required after significant changes | Active |

---

## Status Definitions

- **Active**: Decision is current and governs active code.
- **Superseded**: Replaced by a later decision; retained for historical context.
- **Reverted**: Decision was undone; code no longer reflects it.

---

*Last updated: Priority 3 completion*
