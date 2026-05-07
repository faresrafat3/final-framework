# Real-Time Cognitive Streaming

AIO Framework v8.0.0 introduces a **streaming event layer** that emits structured, real-time events during every graph execution.

## Overview

By default, AIO is batch-oriented: you invoke the graph and receive a final state. With streaming enabled, every LangGraph node emits `START`, `END`, and `DATA` events as the state moves through the 13 cognitive layers.

## Quick Start

### CLI

```bash
aio run "echo hello" --stream
```

This prints NDJSON lines to stdout—one line per event—followed by the final JSON result.

### Programmatic

```python
from aio import build_aio_graph, AIOConfig, make_initial_state, StreamingManager, MemoryTransport

mgr = StreamingManager()
transport = MemoryTransport()
mgr.subscribe(transport)

app = build_aio_graph(AIOConfig(), streaming_manager=mgr)
state = make_initial_state("echo hello")
result = app.invoke(state)

for evt in transport.get_events():
    print(evt["layer"], evt["event_type"], evt["node_name"])
```

## Configuration

| Environment Variable | Default | Description |
|------|---------|-------------|
| `ENABLE_STREAMING` | `false` | Master switch for the streaming subsystem |
| `STREAMING_TRANSPORT` | `memory` | Backend transport: `memory`, `sse`, or `websocket` |
| `STREAMING_EVENT_PERSISTENCE` | `false` | Optional persistence: `false` or `redis` |
| `STREAMING_MAX_BUFFER_EVENTS` | `1000` | In-memory ring-buffer size |

All variables can also be set via `AIOConfig.streaming`.

## Event Schema

```python
from aio.streaming import StreamEvent

{
    "layer": "Layer 3 — Planning",
    "event_type": "START",          # START | END | DATA
    "timestamp": "2024-01-01T12:00:00Z",
    "payload": {},
    "trace_id": "abc123...",
    "turn": 1,
    "node_name": "hiplan",
}
```

## Transports

### MemoryTransport

Default in-memory buffer. Useful for testing and lightweight replay.

### SSETransport

Async queue-based transport compatible with FastAPI / Starlette streaming responses.

### WebSocketTransport

Async queue-based transport for bidirectional WebSocket delivery.

### NDJSONTransport

Synchronous transport that writes newline-delimited JSON. Used by the CLI `--stream` flag.

## EventStore (Persistence)

```python
from aio.streaming import EventStore

store = EventStore(backend="redis", redis_url="redis://localhost:6379/0")
store.persist(event)
recent = store.replay(limit=100, trace_id="abc123")
```

If Redis is unavailable, `EventStore` automatically falls back to in-memory storage.

## Dashboard Live Feed

When `GOVERNANCE_DASHBOARD_ENABLE=true` and a `StreamingManager` is passed to `create_dashboard_app`, a WebSocket endpoint at `/ws/live` pushes buffered events to connected clients every 500 ms.

## Architecture

- **Fire-and-forget**: `StreamingManager.emit()` never blocks graph execution.
- **Graceful degradation**: Subscriber exceptions are logged and swallowed.
- **Backward compatibility**: `build_aio_graph(AIOConfig())` without a `streaming_manager` behaves exactly as before.
