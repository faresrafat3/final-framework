from unittest.mock import MagicMock, patch

import pytest

from aio.streaming import EventStore, StreamEvent


class TestEventStore:
    def test_memory_persist_and_replay(self):
        store = EventStore(backend="memory", max_events=5)
        evt = StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={"x": 1})
        store.persist(evt)
        replayed = store.replay(limit=10)
        assert len(replayed) == 1
        assert replayed[0]["payload"]["x"] == 1

    def test_memory_eviction(self):
        store = EventStore(backend="memory", max_events=2)
        for i in range(4):
            store.persist(StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={"i": i}))
        replayed = store.replay(limit=10)
        assert len(replayed) == 2
        assert replayed[0]["payload"]["i"] == 2

    def test_replay_filter_by_trace_id(self):
        store = EventStore(backend="memory")
        store.persist(StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={}, trace_id="t1"))
        store.persist(StreamEvent(layer="L1", event_type="END", timestamp="2024-01-01T00:00:01Z", payload={}, trace_id="t2"))
        replayed = store.replay(trace_id="t1")
        assert len(replayed) == 1
        assert replayed[0]["trace_id"] == "t1"

    def test_redis_unavailable_falls_back_to_memory(self):
        with patch("redis.from_url", side_effect=Exception("no redis")):
            store = EventStore(backend="redis", max_events=3)
            assert store.backend == "memory"
            store.persist(StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={}))
            assert len(store.replay()) == 1

    def test_redis_replay_failure_uses_buffer(self):
        mock_redis = MagicMock()
        mock_redis.ping.return_value = None
        mock_redis.xrevrange.side_effect = Exception("read error")
        with patch("redis.from_url", return_value=mock_redis):
            store = EventStore(backend="redis", max_events=3)
            assert store.backend == "redis"
            store.persist(StreamEvent(layer="L1", event_type="START", timestamp="2024-01-01T00:00:00Z", payload={"x": 2}))
            replayed = store.replay()
            assert len(replayed) == 1
            assert replayed[0]["payload"]["x"] == 2
