"""AIO Framework — Backward-compatible re-export module.

This file preserves the original single-file import interface.
All implementation has moved to the ``aio`` package; this module
simply re-exports every public symbol so existing imports keep working.
"""

from aio import *  # noqa: F401,F403
from aio import (
    build_aio_graph,
    AIOConfig,
    make_initial_state,
    AIOState,
    ObservabilityLayer,
    ObservabilityConfig,
    ContextManager,
    ContextConfig,
    MemoryBridge,
    MemoryConfig,
    BaseMemoryBackend,
    InMemoryBackend,
    RedisBackend,
    PostgresBackend,
    HybridBackend,
    PlanningLayer,
    PlanningConfig,
    HiPlanPlanner,
    FLARELookahead,
    LWMPlanner,
    PPAPlanner,
    SPIRALPlanner,
    MARSReflector,
    MACIMetaPlanner,
    VMAOPlanner,
    LLMPlanner,
    CuriosityEngine,
    CuriosityConfig,
    Verifier,
    VerifierConfig,
    ToolOptimizer,
    ToolOptimizerConfig,
    ToolGate,
    ToolGateConfig,
    FailureRecovery,
    FailureRecoveryConfig,
    FailureState,
    SelfEvolutionLayer,
    SelfEvolutionConfig,
    MultiAgentCoordinator,
    MultiAgentConfig,
    SafetyGovernance,
    SafetyGovernanceConfig,
    CognitiveImmuneSystem,
    CognitiveImmuneConfig,
    ImmuneLearningEngine,
    GovernanceDashboardConfig,
    MCPConfig,
    MCPServerConfig,
    AuditStore,
    create_dashboard_app,
    MCPClient,
    MCPTransport,
    StdioTransport,
    SSETransport,
    node_mcp_discover,
    node_context_ingest,
    node_context_sculpt,
    node_memory_retrieve,
    node_memory_encode,
    node_memory_verify,
    node_memory_store,
    node_memory_consolidate,
    node_plan_generate,
    node_maci_select,
    node_hiplan,
    node_flare,
    node_lwm_augment,
    node_ppa_analyze,
    node_spiral_mcts,
    node_mars_reflect,
    node_vmao_decompose,
    node_curiosity_intrinsic,
    node_curiosity_seek,
    node_curiosity_serendipity,
    node_curiosity_counterfactual,
    node_curiosity_umwelt,
    node_verify_plan,
    node_debug_and_replan,
    node_gstep_evaluate,
    node_hdpo_optimize,
    node_jtpro_optimize,
    node_sandbox_execute,
    node_analytics_record,
    node_execute_action,
    node_failure_assess,
    node_retry_with_backoff,
    node_escalate,
    node_graceful_degrade,
    node_neuroshield,
    node_failure_learn,
    node_finalize_output,
    node_self_evolution_analyze,
    node_multi_agent_decompose,
    node_multi_agent_dispatch,
    node_multi_agent_aggregate,
    node_multi_agent_synthesize,
    node_safety_governance_audit,
    node_cognitive_immune_scan,
    route_memory_confidence,
    route_verification,
    route_failure,
    route_shield,
    route_ppa,
    route_gstep,
    route_post_execution,
    route_context_priority,
    route_multi_agent,
    route_safety_governance,
    route_post_finalize,
    route_self_evolution,
    OTEL_AVAILABLE,
    PROMETHEUS_AVAILABLE,
    DOCKER_AVAILABLE,
    LANGSMITH_AVAILABLE,
    SENTENCE_TRANSFORMERS_AVAILABLE,
    LANGCHAIN_OPENAI_AVAILABLE,
    LANGCHAIN_ANTHROPIC_AVAILABLE,
    LANGCHAIN_CHAT_AVAILABLE,
    REDIS_AVAILABLE,
    PSYCOPG2_AVAILABLE,
    DEFAULT_MCP_ENABLE,
    DEFAULT_MCP_SERVERS_JSON,
    DEFAULT_MCP_TIMEOUT_SECONDS,
    HTTPX_AVAILABLE,
    _NullContext,
)

# Re-export END so integration tests that import it from here keep working.
from langgraph.graph import END  # noqa: F401

# Re-export optional dependency symbols on this module so that existing
# tests that patch e.g. ``aio_framework.Counter`` or
# ``aio_framework.SentenceTransformer`` continue to work.
from aio.config.deps import (
    Counter as _Counter,
    Histogram as _Histogram,
    Gauge as _Gauge,
    start_http_server as _start_http_server,
    SentenceTransformer as _SentenceTransformer,
    ChatOpenAI as _ChatOpenAI,
    ChatAnthropic as _ChatAnthropic,
    LangSmithClient as _LangSmithClient,
    docker as _docker_mod,
    trace as _trace_mod,
    redis as _redis_mod,
    psycopg2 as _psycopg2_mod,
)

# Assign to module-level names so ``patch("aio_framework.X")`` resolves.
Counter = _Counter
Histogram = _Histogram
Gauge = _Gauge
start_http_server = _start_http_server
SentenceTransformer = _SentenceTransformer
ChatOpenAI = _ChatOpenAI
ChatAnthropic = _ChatAnthropic
LangSmithClient = _LangSmithClient
docker = _docker_mod
trace = _trace_mod
redis = _redis_mod
psycopg2 = _psycopg2_mod


def run_aio(raw_input: str, session_id: str | None = None, config: AIOConfig | None = None) -> AIOState:  # type: ignore[name-defined]
    app = build_aio_graph(config)
    state = make_initial_state(raw_input, session_id)
    result = app.invoke(state)
    return result


if __name__ == "__main__":
    import json
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "echo hello world"
    final_state = run_aio(query)
    print(json.dumps({k: v for k, v in final_state.items() if k != "metrics"}, indent=2, default=str))
