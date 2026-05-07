from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .events import StreamEvent


class EventStore:
    """Optional persistence layer for :class:`StreamEvent` instances.

    Supports two backends:

    * ``memory`` — in-process list with TTL-based eviction (default).
    * ``redis`` — append to a Redis stream/list with graceful fallback to
      in-memory if Redis is unavailable.

    Args:
        backend: ``memory`` or ``redis``.
        redis_url: Connection string when backend is ``redis``.
        max_events: Maximum events retained in the in-memory buffer.
    """

    def __init__(
        self,
        backend: str = "memory",
        redis_url: Optional[str] = None,
        max_events: int = 10000,
    ) -> None:
        self.backend = backend
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self.max_events = max_events
        self._buffer: List[StreamEvent] = []
        self._redis: Any = None
        self._logger = logging.getLogger("aio.streaming.store")

        if self.backend == "redis":
            try:
                import redis as _redis
                self._redis = _redis.from_url(self.redis_url)
                self._redis.ping()
            except Exception as exc:
                self._logger.warning("Redis unavailable for EventStore (%s); falling back to memory.", exc)
                self.backend = "memory"
                self._redis = None

    def persist(self, event: StreamEvent) -> None:
        """Store a single event."""
        if self.backend == "redis" and self._redis is not None:
            try:
                self._redis.xadd("aio:events", {"data": str(event)}, maxlen=self.max_events, approximate=True)
                return
            except Exception as exc:
                self._logger.warning("Redis persist failed (%s); falling back to memory.", exc)
        self._buffer.append(event)
        if len(self._buffer) > self.max_events:
            self._buffer.pop(0)

    def replay(
        self,
        limit: int = 100,
        trace_id: Optional[str] = None,
    ) -> List[StreamEvent]:
        """Return recent events, optionally filtered by ``trace_id``."""
        events: List[StreamEvent] = []
        if self.backend == "redis" and self._redis is not None:
            try:
                entries = self._redis.xrevrange("aio:events", count=limit)
                for entry in entries:
                    _, fields = entry
                    raw = fields.get(b"data", b"{}").decode()
                    import json

                    data = json.loads(raw)
                    events.append(StreamEvent(**data))
            except Exception as exc:
                self._logger.warning("Redis replay failed (%s); using memory buffer.", exc)
        if not events:
            events = list(self._buffer)
        if trace_id is not None:
            events = [e for e in events if e.get("trace_id") == trace_id]
        return events[-limit:]
