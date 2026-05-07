from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict


class StreamEvent(TypedDict, total=False):
    """Structured event emitted by every cognitive layer during graph execution.

    Fields:
        layer: Human-readable layer name (e.g. ``Layer 1 — Context``).
        event_type: One of ``START``, ``END``, ``DATA``.
        timestamp: ISO-8601 UTC timestamp.
        payload: Free-form event payload (state slice, metadata, etc.).
        trace_id: 32-hex trace ID correlated with the state.
        turn: Turn counter from the state.
        node_name: Optional LangGraph node name that emitted the event.
    """

    layer: str
    event_type: str
    timestamp: str
    payload: Dict[str, Any]
    trace_id: Optional[str]
    turn: Optional[int]
    node_name: Optional[str]
