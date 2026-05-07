from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from .events import StreamEvent


class MemoryTransport:
    """Default in-memory transport that buffers events for testing and replay."""

    def __init__(self, max_events: int = 1000) -> None:
        self._events: List[StreamEvent] = []
        self.max_events = max_events
        self._logger = logging.getLogger("aio.streaming.memory_transport")

    def __call__(self, event: StreamEvent) -> None:
        self._events.append(event)
        if len(self._events) > self.max_events:
            self._events.pop(0)

    def get_events(self) -> List[StreamEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()


class SSETransport:
    """Server-Sent Events transport compatible with FastAPI / Starlette.

    Events are pushed into an internal ``asyncio.Queue``.  A background task
    can drain the queue and yield ``data: <json>\n\n`` formatted lines.
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        self._queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._logger = logging.getLogger("aio.streaming.sse_transport")

    def __call__(self, event: StreamEvent) -> None:
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._logger.warning("SSE transport queue full; dropping event.")

    async def stream(self):
        """Async generator yielding SSE-formatted lines."""
        while True:
            event = await self._queue.get()
            yield f"data: {json.dumps(event, default=str)}\n\n"


class WebSocketTransport:
    """Bidirectional WebSocket transport.

    Events are pushed into an internal ``asyncio.Queue``.  A handler can
    await :meth:`next_event` and send JSON over an open WebSocket connection.
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        self._queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._logger = logging.getLogger("aio.streaming.websocket_transport")

    def __call__(self, event: StreamEvent) -> None:
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._logger.warning("WebSocket transport queue full; dropping event.")

    async def next_event(self) -> StreamEvent:
        return await self._queue.get()

    def subscribe(self, manager: "StreamingManager") -> None:
        manager.subscribe(self)

    def unsubscribe(self, manager: "StreamingManager") -> None:
        manager.unsubscribe(self)


class NDJSONTransport:
    """Synchronous NDJSON transport that writes ``\n``-delimited JSON lines.

    Used by the CLI ``--stream`` flag to print events to stdout.
    """

    def __init__(self, file: Any = None) -> None:
        self.file = file
        self._logger = logging.getLogger("aio.streaming.ndjson_transport")

    def __call__(self, event: StreamEvent) -> None:
        try:
            line = json.dumps(event, default=str)
            if self.file is not None:
                self.file.write(line + "\n")
                self.file.flush()
            else:
                print(line)
        except Exception as exc:
            self._logger.warning("NDJSON transport write failed: %s", exc)
