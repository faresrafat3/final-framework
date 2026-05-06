import pytest

from aio_framework import (
    AIOConfig,
    ContextManager,
    MemoryBridge,
    Verifier,
    ToolGate,
    FailureRecovery,
    ObservabilityLayer,
    ObservabilityConfig,
    PlanningLayer,
    node_context_ingest,
    node_context_sculpt,
    node_memory_retrieve,
    node_memory_encode,
    node_memory_verify,
    node_memory_store,
    node_memory_consolidate,
    node_plan_generate,
    node_verify_plan,
    node_execute_action,
    node_failure_assess,
    node_retry_with_backoff,
    node_neuroshield,
    node_finalize_output,
    make_initial_state,
    route_memory_confidence,
    route_verification,
    route_failure,
)


@pytest.fixture
def deps():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    cfg = AIOConfig()
    return {
        "obs": obs,
        "ctx": ContextManager(cfg.context, obs),
        "mem": MemoryBridge(cfg.memory, obs),
        "verifier": Verifier(cfg.verifier, obs),
        "toolgate": ToolGate(cfg.toolgate, obs),
        "recovery": FailureRecovery(cfg.failure_recovery, obs),
        "planning": PlanningLayer(cfg.planning, obs),
    }


class TestLayerInteractions:
    def test_context_to_memory_flow(self, deps):
        state = make_initial_state("analyze the error log")
        state = node_context_ingest(state, deps["ctx"])
        state = node_context_sculpt(state, deps["ctx"])
        state = node_memory_encode(state, deps["mem"])
        state = node_memory_verify(state, deps["mem"])
        state = node_memory_store(state, deps["mem"])
        assert state["intent"] == "analysis"
        assert len(deps["mem"]._episodic) >= 1

    def test_memory_retrieve_routes_to_encode_when_low_confidence(self, deps):
        state = make_initial_state("something unknown")
        state = node_memory_retrieve(state, deps["mem"])
        assert route_memory_confidence(state) == "memory_encode"

    def test_memory_retrieve_routes_to_plan_when_high_confidence(self, deps):
        state = make_initial_state("hello")
        deps["mem"]._episodic["h"] = {
            "id": "h", "content": "hello",
            "timestamp": __import__('time').time(),
            "embedding": deps["mem"]._embed("hello"),
            "importance": 0.9, "verification_passed": True,
        }
        deps["mem"]._index_keywords("h", "hello")
        state = node_memory_retrieve(state, deps["mem"])
        assert route_memory_confidence(state) == "curiosity_intrinsic"

    def test_plan_to_verify_to_execute_flow(self, deps):
        state = make_initial_state("echo hello")
        state = node_context_ingest(state, deps["ctx"])
        state = node_context_sculpt(state, deps["ctx"])
        state = node_plan_generate(state, deps["planning"])
        state = node_verify_plan(state, deps["verifier"])
        assert route_verification(state) in {"execute_action", "debug_and_replan"}
        if route_verification(state) == "execute_action":
            state = node_execute_action(state, deps["toolgate"])
            assert "execution_result" in state

    def test_execution_failure_triggers_recovery(self, deps):
        state = make_initial_state("")
        state["execution_result"] = {"stderr": "connection reset", "exit_code": 1, "success": False}
        state = node_failure_assess(state, deps["recovery"])
        assert state["failure_state"] in {"DEGRADED", "RECOVERING", "FAILED"}
        route = route_failure(state)
        assert route in {"retry_with_backoff", "escalate", "graceful_degrade"}

    def test_retry_resets_to_verify(self, deps):
        state = make_initial_state("")
        state["failure_count"] = 1
        state = node_retry_with_backoff(state, deps["recovery"])
        assert "retry_backoff_seconds" in state["metrics"]

    def test_neuroshield_blocks_then_escalates(self, deps):
        state = make_initial_state("rm -rf /")
        state = node_neuroshield(state, deps["recovery"])
        assert state["failure_state"] == "FAILED"
        assert len(state.get("safety_violations", [])) > 0

    def test_full_cycle_happy_path(self, deps):
        state = make_initial_state("echo test")
        state = node_context_ingest(state, deps["ctx"])
        state = node_context_sculpt(state, deps["ctx"])
        state = node_neuroshield(state, deps["recovery"])
        assert not state.get("safety_violations")
        state = node_memory_retrieve(state, deps["mem"])
        state = node_memory_encode(state, deps["mem"])
        state = node_memory_verify(state, deps["mem"])
        state = node_memory_store(state, deps["mem"])
        state = node_memory_consolidate(state, deps["mem"])
        state = node_plan_generate(state, deps["planning"])
        state = node_verify_plan(state, deps["verifier"])
        state = node_execute_action(state, deps["toolgate"])
        state = node_failure_assess(state, deps["recovery"])
        state = node_finalize_output(state)
        assert state["output"] is not None
