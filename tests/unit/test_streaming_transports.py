import asyncio

import pytest

from aio.streaming import MemoryTransport, SSETransport, WebSocketTransport, NDJSONTransport, StreamEvent


class TestMemoryTransport:
    def test_buffers_events(self):
        t = MemoryTransport(max_events=3)
        t(StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={}))
        t(StreamEvent(layer="L1", event_type="END", timestamp="2024-01-01T00:00:01Z", payload={}))
        assert len(t.get_events()) == 2

    def test_eviction(self):
        t = MemoryTransport(max_events=2)
        for i in range(4):
            t(StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={"i": i}))
        events = t.get_events()
        assert len(events) == 2
        assert events[0]["payload"]["i"] == 2


class TestSSETransport:
    @pytest.mark.asyncio
    async def test_stream_yields_data_lines(self):
        transport = SSETransport()
        transport(StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={"a": 1}))

        lines = []
        async for line in transport.stream():
            lines.append(line)
            if len(lines) >= 1:
                break

        assert len(lines) == 1
        assert lines[0].startswith("data: {")

    def test_queue_full_graceful(self):
        transport = SSETransport(max_queue_size=1)
        transport(StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={}))
        transport(StreamEvent(layer="L1", event_type="END", timestamp="2024-01-01T00:00:01Z", payload={}))


class TestWebSocketTransport:
    @pytest.mark.asyncio
    async def test_next_event(self):
        transport = WebSocketTransport()
        evt = StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={})
        transport(evt)
        result = await asyncio.wait_for(transport.next_event(), timeout=1.0)
        assert result["layer"] == "L1"


class TestNDJSONTransport:
    def test_writes_to_file(self, tmp_path):
        f = tmp_path / "out.ndjson"
        with open(f, "w") as fh:
            t = NDJSONTransport(file=fh)
            t(StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={"x": 1}))

        with open(f) as fh:
            lines = fh.readlines()
        assert len(lines) == 1
        assert '"layer": "L1"' in lines[0]
