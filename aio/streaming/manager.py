from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from .events import StreamEvent


class StreamingManager:
    """Async-safe pub/sub registry for :class:`StreamEvent` instances.

    Subscribers register callbacks via :meth:`subscribe`.  Events are
    emitted fire-and-forget via :meth:`emit` so that graph execution is
    never blocked by slow transports.

    An in-memory ring buffer retains the most recent events up to
    ``max_buffer_events`` for testing and replay.
    """

    def __init__(self, max_buffer_events: int = 1000) -> None:
        self._subscribers: List[Callable[[StreamEvent], Any]] = []
        self._buffer: List[StreamEvent] = []
        self.max_buffer_events = max_buffer_events
        self._logger = logging.getLogger("aio.streaming")

    def subscribe(self, callback: Callable[[StreamEvent], Any]) -> None:
        """Register a callback that receives every emitted event."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[StreamEvent], Any]) -> None:
        """Remove a previously registered callback."""
        try:
            self._subscribers.remove(callback)
        except ValueError:
            pass

    def emit(self, event: StreamEvent) -> None:
        """Fire-and-forget emit to all subscribers and the local buffer.

        Synchronous callbacks are invoked directly.  Coroutine callbacks are
        scheduled via ``asyncio.create_task`` when an event loop is running.
        """
        self._buffer.append(event)
        if len(self._buffer) > self.max_buffer_events:
            self._buffer.pop(0)

        for cb in list(self._subscribers):
            try:
                result = cb(event)
                if asyncio.iscoroutine(result):
                    try:
                        asyncio.get_running_loop()
                        asyncio.create_task(result)
                    except RuntimeError:
                        pass
            except Exception as exc:
                self._logger.warning("Streaming subscriber failed: %s", exc)

    def get_buffer(self) -> List[StreamEvent]:
        """Return a shallow copy of the current in-memory buffer."""
        return list(self._buffer)

    def clear_buffer(self) -> None:
        """Drop all buffered events."""
        self._buffer.clear()

    @staticmethod
    def make_event(
        layer: str,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        turn: Optional[int] = None,
        node_name: Optional[str] = None,
    ) -> StreamEvent:
        """Build a :class:`StreamEvent` with an auto-generated timestamp."""
        return StreamEvent(
            layer=layer,
            event_type=event_type,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            payload=payload or {},
            trace_id=trace_id,
            turn=turn,
            node_name=node_name,
        )
