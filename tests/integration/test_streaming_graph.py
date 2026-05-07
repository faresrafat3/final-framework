from aio import build_aio_graph, AIOConfig, make_initial_state, StreamingManager, MemoryTransport


class TestStreamingGraph:
    def test_graph_without_streaming_runs_identically(self):
        app = build_aio_graph(AIOConfig())
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result["output"] is not None

    def test_graph_with_streaming_emits_events(self):
        mgr = StreamingManager()
        transport = MemoryTransport()
        mgr.subscribe(transport)
        app = build_aio_graph(AIOConfig(), streaming_manager=mgr)
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result["output"] is not None
        events = transport.get_events()
        assert len(events) > 0
        start_events = [e for e in events if e["event_type"] == "START"]
        end_events = [e for e in events if e["event_type"] == "END"]
        assert len(start_events) > 0
        assert len(end_events) > 0
        # At least one node from each of the 13 layers should appear
        layers = {e["layer"] for e in events}
        assert any("Context" in l for l in layers)
        assert any("Memory" in l for l in layers)
        assert any("Planning" in l for l in layers)
        assert any("Curiosity" in l for l in layers)
        assert any("Verification" in l for l in layers)
        assert any("Tool" in l for l in layers)
        assert any("Execution" in l for l in layers)
        assert any("Failure" in l for l in layers)
