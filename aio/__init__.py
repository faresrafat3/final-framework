"""AIO Framework — Modularized core with backward-compatible re-exports.

This package exposes the public API surface of the All-in-One Agentic
Framework.  The typical entry points for developers are:

* :class:`aio.config.models.AIOConfig` – typed Pydantic configuration
* :func:`aio.graph.builder.build_aio_graph` – compile the full LangGraph
* :class:`aio.state.AIOState` – the typed state dict consumed by every node
* Layer classes such as :class:`aio.layers.observability.ObservabilityLayer`,
  :class:`aio.layers.memory.MemoryBridge`, etc.

Example::

    from aio import AIOConfig, build_aio_graph, make_initial_state

    config = AIOConfig()
    graph = build_aio_graph(config)
    state = make_initial_state("echo hello world")
    result = graph.invoke(state)
"""

from .config.models import (
    AIOConfig,
    ObservabilityConfig,
    ContextConfig,
    MemoryConfig,
    PlanningConfig,
    CuriosityConfig,
    VerifierConfig,
    ToolOptimizerConfig,
    ToolGateConfig,
    FailureRecoveryConfig,
    SelfEvolutionConfig,
    MultiAgentConfig,
    SafetyGovernanceConfig,
    CognitiveImmuneConfig,
    NeuroSymbolicConfig,
    GovernanceDashboardConfig,
    MCPConfig,
    MCPServerConfig,
    BenchmarkConfig,
    StreamingConfig,
    HitlConfig,
)
from .config.deps import (
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
    DEFAULT_OTEL_ENDPOINT,
    DEFAULT_SERVICE_NAME,
    DEFAULT_PROMETHEUS_PORT,
    DEFAULT_LANGCHAIN_PROJECT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_LOG_LEVEL,
    DEFAULT_SAFETY_MODE,
    DEFAULT_DOCKER_SOCKET,
    DEFAULT_MEMBRIDGE_CONN,
    ENABLE_LLM_PLANNING,
    LLM_PLANNER_PROVIDER,
    LLM_PLANNER_MODEL,
    LLM_PLANNER_TEMPERATURE,
    LLM_PLANNER_MAX_TOKENS,
    DEFAULT_MCP_ENABLE,
    DEFAULT_MCP_SERVERS_JSON,
    DEFAULT_MCP_TIMEOUT_SECONDS,
    DEFAULT_NEURO_SYMBOLIC_ENABLE,
    DEFAULT_HITL_ENABLE,
    HTTPX_AVAILABLE,
    PSUTIL_AVAILABLE,
    JINJA2_AVAILABLE,
)
from .layers.observability import ObservabilityLayer, _NullContext
from .layers.context import ContextManager
from .layers.memory import MemoryBridge
from .layers.memory_backends import (
    BaseMemoryBackend,
    InMemoryBackend,
    RedisBackend,
    PostgresBackend,
    HybridBackend,
)
from .layers.planning import (
    PlanningLayer,
    HiPlanPlanner,
    FLARELookahead,
    LWMPlanner,
    PPAPlanner,
    SPIRALPlanner,
    MARSReflector,
    MACIMetaPlanner,
    VMAOPlanner,
    LLMPlanner,
)
from .layers.curiosity import CuriosityEngine
from .layers.verification import Verifier
from .layers.tool_optimizer import ToolOptimizer
from .layers.tool_gate import ToolGate
from .layers.mcp_client import MCPClient, MCPTransport, StdioTransport, SSETransport, node_mcp_discover
from .layers.failure_recovery import FailureRecovery, FailureState
from .layers.self_evolution import SelfEvolutionLayer
from .layers.multi_agent import MultiAgentCoordinator
from .layers.multi_agent_backend import SimulatedMultiAgentBackend, LangGraphMultiAgentBackend
from .layers.safety_governance import SafetyGovernance
from .layers.cognitive_immune import CognitiveImmuneSystem
from .layers.immune_learning import ImmuneLearningEngine
from .layers.neuro_symbolic import (
    NeuroSymbolicMandate,
    SymbolicEngine,
    SymbolicRule,
    KnowledgeGraph,
    FormalVerifier,
)
from .layers.hitl import (
    HitlGate,
    FeedbackCollector,
    EscalationPolicy,
    FeedbackLoopEngine,
)
from .state import AIOState, make_initial_state
from .graph.builder import build_aio_graph
from .dashboard.store import AuditStore

try:
    from .dashboard.app import create_dashboard_app
except Exception:  # pragma: no cover
    create_dashboard_app = None  # type: ignore[misc,assignment]

try:
    from .streaming import (
        StreamEvent,
        StreamingManager,
        MemoryTransport,
        SSETransport,
        WebSocketTransport,
        NDJSONTransport,
        EventStore,
    )
except Exception:  # pragma: no cover
    StreamEvent = None  # type: ignore[misc,assignment]
    StreamingManager = None  # type: ignore[misc,assignment]
    MemoryTransport = None  # type: ignore[misc,assignment]
    SSETransport = None  # type: ignore[misc,assignment]
    WebSocketTransport = None  # type: ignore[misc,assignment]
    NDJSONTransport = None  # type: ignore[misc,assignment]
    EventStore = None  # type: ignore[misc,assignment]

try:
    from .benchmark import (
        BenchmarkCollector,
        BenchmarkRunner,
        JSONReporter,
        HTMLReporter,
        RegressionDetector,
        main as benchmark_main,
    )
except Exception:  # pragma: no cover
    BenchmarkCollector = None  # type: ignore[misc,assignment]
    BenchmarkRunner = None  # type: ignore[misc,assignment]
    JSONReporter = None  # type: ignore[misc,assignment]
    HTMLReporter = None  # type: ignore[misc,assignment]
    RegressionDetector = None  # type: ignore[misc,assignment]
    benchmark_main = None  # type: ignore[misc,assignment]

from .graph.nodes import (
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
    node_neuro_symbolic_parse,
    node_neuro_symbolic_infer,
    node_neuro_symbolic_ground,
    node_neuro_symbolic_verify,
    node_neuro_symbolic_synthesize,
    node_hitl_gate,
    node_hitl_wait,
    node_feedback_collect,
    node_escalation_policy,
    node_feedback_loop,
)
from .graph.routing import (
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
    route_neuro_symbolic,
    route_post_neuro_symbolic,
    route_hitl,
    route_escalation_policy,
)

__all__ = [
    "AIOConfig",
    "ObservabilityConfig",
    "ContextConfig",
    "MemoryConfig",
    "PlanningConfig",
    "CuriosityConfig",
    "VerifierConfig",
    "ToolOptimizerConfig",
    "ToolGateConfig",
    "FailureRecoveryConfig",
    "SelfEvolutionConfig",
    "MultiAgentConfig",
    "SafetyGovernanceConfig",
    "CognitiveImmuneConfig",
    "NeuroSymbolicConfig",
    "GovernanceDashboardConfig",
    "MCPConfig",
    "MCPServerConfig",
    "StreamingConfig",
    "OTEL_AVAILABLE",
    "PROMETHEUS_AVAILABLE",
    "DOCKER_AVAILABLE",
    "LANGSMITH_AVAILABLE",
    "SENTENCE_TRANSFORMERS_AVAILABLE",
    "LANGCHAIN_OPENAI_AVAILABLE",
    "LANGCHAIN_ANTHROPIC_AVAILABLE",
    "LANGCHAIN_CHAT_AVAILABLE",
    "REDIS_AVAILABLE",
    "PSYCOPG2_AVAILABLE",
    "DEFAULT_OTEL_ENDPOINT",
    "DEFAULT_SERVICE_NAME",
    "DEFAULT_PROMETHEUS_PORT",
    "DEFAULT_LANGCHAIN_PROJECT",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_SAFETY_MODE",
    "DEFAULT_DOCKER_SOCKET",
    "DEFAULT_MEMBRIDGE_CONN",
    "ENABLE_LLM_PLANNING",
    "LLM_PLANNER_PROVIDER",
    "LLM_PLANNER_MODEL",
    "LLM_PLANNER_TEMPERATURE",
    "LLM_PLANNER_MAX_TOKENS",
    "DEFAULT_MCP_ENABLE",
    "DEFAULT_MCP_SERVERS_JSON",
    "DEFAULT_MCP_TIMEOUT_SECONDS",
    "DEFAULT_NEURO_SYMBOLIC_ENABLE",
    "DEFAULT_HITL_ENABLE",
    "HTTPX_AVAILABLE",
    "PSUTIL_AVAILABLE",
    "JINJA2_AVAILABLE",
    "ObservabilityLayer",
    "_NullContext",
    "ContextManager",
    "MemoryBridge",
    "BaseMemoryBackend",
    "InMemoryBackend",
    "RedisBackend",
    "PostgresBackend",
    "HybridBackend",
    "PlanningLayer",
    "HiPlanPlanner",
    "FLARELookahead",
    "LWMPlanner",
    "PPAPlanner",
    "SPIRALPlanner",
    "MARSReflector",
    "MACIMetaPlanner",
    "VMAOPlanner",
    "LLMPlanner",
    "CuriosityEngine",
    "Verifier",
    "ToolOptimizer",
    "ToolGate",
    "MCPClient",
    "MCPTransport",
    "StdioTransport",
    "SSETransport",
    "node_mcp_discover",
    "FailureRecovery",
    "FailureState",
    "SelfEvolutionLayer",
    "MultiAgentCoordinator",
    "SimulatedMultiAgentBackend",
    "LangGraphMultiAgentBackend",
    "SafetyGovernance",
    "CognitiveImmuneSystem",
    "ImmuneLearningEngine",
    "NeuroSymbolicMandate",
    "SymbolicEngine",
    "SymbolicRule",
    "KnowledgeGraph",
    "FormalVerifier",
    "HitlGate",
    "FeedbackCollector",
    "EscalationPolicy",
    "FeedbackLoopEngine",
    "AuditStore",
    "create_dashboard_app",
    "BenchmarkConfig",
    "BenchmarkCollector",
    "BenchmarkRunner",
    "JSONReporter",
    "HTMLReporter",
    "RegressionDetector",
    "benchmark_main",
    "StreamEvent",
    "StreamingManager",
    "MemoryTransport",
    "SSETransport",
    "WebSocketTransport",
    "NDJSONTransport",
    "EventStore",
    "AIOState",
    "make_initial_state",
    "build_aio_graph",
    "node_context_ingest",
    "node_context_sculpt",
    "node_memory_retrieve",
    "node_memory_encode",
    "node_memory_verify",
    "node_memory_store",
    "node_memory_consolidate",
    "node_plan_generate",
    "node_maci_select",
    "node_hiplan",
    "node_flare",
    "node_lwm_augment",
    "node_ppa_analyze",
    "node_spiral_mcts",
    "node_mars_reflect",
    "node_vmao_decompose",
    "node_curiosity_intrinsic",
    "node_curiosity_seek",
    "node_curiosity_serendipity",
    "node_curiosity_counterfactual",
    "node_curiosity_umwelt",
    "node_verify_plan",
    "node_debug_and_replan",
    "node_gstep_evaluate",
    "node_hdpo_optimize",
    "node_jtpro_optimize",
    "node_sandbox_execute",
    "node_analytics_record",
    "node_execute_action",
    "node_failure_assess",
    "node_retry_with_backoff",
    "node_escalate",
    "node_graceful_degrade",
    "node_neuroshield",
    "node_failure_learn",
    "node_finalize_output",
    "node_self_evolution_analyze",
    "node_multi_agent_decompose",
    "node_multi_agent_dispatch",
    "node_multi_agent_aggregate",
    "node_multi_agent_synthesize",
    "node_safety_governance_audit",
    "node_cognitive_immune_scan",
    "node_neuro_symbolic_parse",
    "node_neuro_symbolic_infer",
    "node_neuro_symbolic_ground",
    "node_neuro_symbolic_verify",
    "node_neuro_symbolic_synthesize",
    "node_hitl_gate",
    "node_hitl_wait",
    "node_feedback_collect",
    "node_escalation_policy",
    "node_feedback_loop",
    "route_memory_confidence",
    "route_verification",
    "route_failure",
    "route_shield",
    "route_ppa",
    "route_gstep",
    "route_post_execution",
    "route_context_priority",
    "route_multi_agent",
    "route_safety_governance",
    "route_post_finalize",
    "route_self_evolution",
    "route_neuro_symbolic",
    "route_post_neuro_symbolic",
    "route_hitl",
    "route_escalation_policy",
]
