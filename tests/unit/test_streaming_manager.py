import pytest

from aio.streaming import StreamingManager, StreamEvent


class TestStreamingManager:
    def test_make_event_returns_typed_dict(self):
        event = StreamingManager.make_event(
            layer="Layer 1 — Context",
            event_type="START",
            payload={"node": "context_ingest"},
            trace_id="abc123",
            turn=1,
            node_name="context_ingest",
        )
        assert event["layer"] == "Layer 1 — Context"
        assert event["event_type"] == "START"
        assert event["payload"]["node"] == "context_ingest"
        assert event["trace_id"] == "abc123"
        assert event["turn"] == 1
        assert event["node_name"] == "context_ingest"
        assert "timestamp" in event

    def test_subscribe_and_emit(self):
        mgr = StreamingManager()
        received = []

        def cb(event: StreamEvent):
            received.append(event)

        mgr.subscribe(cb)
        evt = StreamingManager.make_event("L1", "START")
        mgr.emit(evt)
        assert len(received) == 1
        assert received[0]["layer"] == "L1"

    def test_unsubscribe(self):
        mgr = StreamingManager()
        received = []

        def cb(event: StreamEvent):
            received.append(event)

        mgr.subscribe(cb)
        mgr.unsubscribe(cb)
        mgr.emit(StreamingManager.make_event("L1", "START"))
        assert len(received) == 0

    def test_buffer_respects_max(self):
        mgr = StreamingManager(max_buffer_events=3)
        for i in range(5):
            mgr.emit(StreamingManager.make_event("L1", "START", payload={"i": i}))
        buf = mgr.get_buffer()
        assert len(buf) == 3
        assert buf[0]["payload"]["i"] == 2

    def test_clear_buffer(self):
        mgr = StreamingManager()
        mgr.emit(StreamingManager.make_event("L1", "START"))
        mgr.clear_buffer()
        assert mgr.get_buffer() == []

    def test_subscriber_exception_does_not_break_emit(self):
        mgr = StreamingManager()

        def bad(event: StreamEvent):
            raise RuntimeError("boom")

        def good(event: StreamEvent):
            good.called = True

        good.called = False
        mgr.subscribe(bad)
        mgr.subscribe(good)
        mgr.emit(StreamingManager.make_event("L1", "START"))
        assert good.called is True
