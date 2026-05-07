from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field

from .deps import (
    DEFAULT_OTEL_ENDPOINT,
    DEFAULT_SERVICE_NAME,
    DEFAULT_PROMETHEUS_PORT,
    DEFAULT_LANGCHAIN_PROJECT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_LOG_LEVEL,
    DEFAULT_SAFETY_MODE,
    DEFAULT_DOCKER_SOCKET,
    DEFAULT_MEMBRIDGE_CONN,
    DEFAULT_MCP_ENABLE,
    DEFAULT_MCP_SERVERS_JSON,
    DEFAULT_MCP_TIMEOUT_SECONDS,
)


class ObservabilityConfig(BaseModel):
    """Layer 0 configuration for OpenTelemetry, Prometheus, and LangSmith.

    Attributes:
        otel_endpoint: OTLP gRPC endpoint for the OpenTelemetry collector.
        service_name: Logical service name attached to every trace.
        prometheus_port: Port exposed by the in-process Prometheus metrics server.
        log_level: Python logging level (``DEBUG``, ``INFO``, ``WARNING``, etc.).
        enable_langsmith: Whether to forward runs to LangSmith when the API key is present.
        langchain_project: LangSmith project label.
    """

    otel_endpoint: str = DEFAULT_OTEL_ENDPOINT
    service_name: str = DEFAULT_SERVICE_NAME
    prometheus_port: int = DEFAULT_PROMETHEUS_PORT
    log_level: str = DEFAULT_LOG_LEVEL
    enable_langsmith: bool = Field(default_factory=lambda: bool(os.getenv("LANGCHAIN_API_KEY")))
    langchain_project: str = DEFAULT_LANGCHAIN_PROJECT


class ContextConfig(BaseModel):
    """Layer 1 configuration for token-aware context management and BAPO routing.

    Attributes:
        max_tokens: Hard context-window size in tokens.
        budget_reserve: Tokens reserved for system overhead.
        prune_threshold: Fraction of the window that must be free after pruning.
        bapo_default_attention: Default attention weight for the BAPO map.
    """

    max_tokens: int = 4096
    budget_reserve: int = 512
    prune_threshold: float = 0.3
    bapo_default_attention: float = 0.5


class MemoryConfig(BaseModel):
    """Layer 2 configuration for the dual-memory bridge.

    Attributes:
        epiphany_ttl_seconds: TTL for episodic entries before they become eligible for consolidation.
        consolidation_batch_size: Max entries promoted to long-term memory per cycle.
        retrieval_top_k: Number of top candidates returned by hybrid search.
        importance_threshold: Minimum importance score required to survive forgetting.
        forget_ttl_seconds: Age after which unimportant entries are purged.
        use_real_embeddings: Whether to load a sentence-transformer model instead of hash-based pseudo embeddings.
        embedding_model_name: Hugging Face model name when ``use_real_embeddings`` is *True*.
        backend_type: Storage backend — ``memory``, ``redis``, ``postgres``, or ``hybrid``.
        redis_url: Connection string for the Redis backend.
        postgres_url: Connection string for the PostgreSQL backend.
    """

    epiphany_ttl_seconds: int = 3600
    consolidation_batch_size: int = 10
    retrieval_top_k: int = 5
    importance_threshold: float = 0.2
    forget_ttl_seconds: int = 86400
    use_real_embeddings: bool = Field(default_factory=lambda: os.getenv("ENABLE_REAL_EMBEDDINGS", "false").lower() == "true")
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2")
    backend_type: str = Field(default_factory=lambda: os.getenv("MEMORY_BACKEND_TYPE", "memory"))
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    postgres_url: str = Field(default_factory=lambda: os.getenv("POSTGRES_URL", "postgresql://localhost/aio"))


class PlanningConfig(BaseModel):
    """Layer 3 configuration for the planning & anti-myopia subsystem.

    Attributes:
        hiplan_max_depth: Maximum depth of the hierarchical goal tree.
        flare_horizon: Number of future steps evaluated by FLARE lookahead.
        spiral_simulations: Number of MCTS rollouts in SPIRAL.
        mars_reflection_depth: Unused depth hint for MARS self-reflection.
        vmao_max_replans: Replanning budget for the VMAO DAG executor.
        enable_llm_planning: Whether to delegate planning to an LLM when available.
        llm_planner_provider: ``openai`` or ``anthropic``.
        llm_planner_model: Model identifier passed to the LLM client.
        llm_planner_temperature: Sampling temperature for LLM planning calls.
        llm_planner_max_tokens: Max tokens per LLM planning call.
    """

    hiplan_max_depth: int = 3
    flare_horizon: int = 3
    spiral_simulations: int = 10
    mars_reflection_depth: int = 1
    vmao_max_replans: int = 3
    enable_llm_planning: bool = Field(default_factory=lambda: os.getenv("ENABLE_LLM_PLANNING", "false").lower() == "true")
    llm_planner_provider: str = Field(default_factory=lambda: os.getenv("LLM_PLANNER_PROVIDER", "openai"))
    llm_planner_model: str = Field(default_factory=lambda: os.getenv("LLM_PLANNER_MODEL", "gpt-4o"))
    llm_planner_temperature: float = Field(default_factory=lambda: float(os.getenv("LLM_PLANNER_TEMPERATURE", "0.2")))
    llm_planner_max_tokens: int = Field(default_factory=lambda: int(os.getenv("LLM_PLANNER_MAX_TOKENS", "1024")))


class CuriosityConfig(BaseModel):
    """Layer 4 configuration for the proactive curiosity engine.

    Attributes:
        novelty_threshold: Minimum novelty score to trigger active seeking.
        intrinsic_reward_weight: Weight applied to the novelty component of the reward.
        serendipity_window: Number of recent plans scanned for unexpected patterns.
        umwelt_constraints: Additional perceptual-boundary constraints beyond the defaults.
    """

    novelty_threshold: float = 0.3
    intrinsic_reward_weight: float = 0.5
    serendipity_window: int = 5
    umwelt_constraints: List[str] = Field(default_factory=list)


class VerifierConfig(BaseModel):
    """Layer 5 configuration for the verification & QA ensemble.

    Attributes:
        ensemble_threshold: Minimum ensemble score for a plan to be considered "passed".
        formal_checks_enabled: Whether deterministic formal rules are evaluated.
        llm_critique_enabled: Whether LLM-based critique is enabled.
        debug_trace_enabled: Whether debug hypotheses are generated on failure.
    """

    ensemble_threshold: float = 0.85
    formal_checks_enabled: bool = True
    llm_critique_enabled: bool = True
    debug_trace_enabled: bool = True


class ToolOptimizerConfig(BaseModel):
    """Layer 6 configuration for tool-use optimisation (G-STEP, HDPO, JTPRO).

    Attributes:
        gstep_threshold: Minimum necessity score; below this the tool gate is skipped.
        hdpo_accuracy_weight: Weight of the accuracy channel in HDPO scoring.
        hdpo_efficiency_weight: Weight of the efficiency channel in HDPO scoring.
        jtpro_iterations: Number of reflective prompt-optimisation iterations.
        auto_deprecation_error_rate: Error rate above which a tool is marked deprecated.
    """

    gstep_threshold: float = 0.3
    hdpo_accuracy_weight: float = 0.6
    hdpo_efficiency_weight: float = 0.4
    jtpro_iterations: int = 3
    auto_deprecation_error_rate: float = 0.2


class ToolGateConfig(BaseModel):
    """Layer 7 configuration for Docker-sandboxed execution.

    Attributes:
        docker_socket: Path or URL of the Docker daemon.
        default_timeout_seconds: Default timeout for a single tool invocation.
        max_memory_mb: Memory limit passed to the Docker container.
        cpu_quota: CPU quota in microseconds per period (Docker ``cpu_quota``).
        network_disabled: Whether network access is blocked inside the sandbox.
        read_only_rootfs: Whether the container root filesystem is mounted read-only.
        registry_path: Optional filesystem path to a custom tool-registry JSON file.
    """

    docker_socket: str = DEFAULT_DOCKER_SOCKET
    default_timeout_seconds: int = 30
    max_memory_mb: int = 512
    cpu_quota: int = 100000
    network_disabled: bool = True
    read_only_rootfs: bool = True
    registry_path: Optional[str] = None


class FailureRecoveryConfig(BaseModel):
    """Layer 8 configuration for failure recovery & anti-fragility.

    Attributes:
        max_retries: Retry budget before permanent failure.
        base_backoff_seconds: Initial backoff between retries.
        max_backoff_seconds: Ceiling for the exponential backoff interval.
        jitter_factor: Random jitter fraction added to backoff.
        safety_mode: NeuroShield enforcement level (``strict``, ``permissive``).
        escalation_threshold: Consecutive failures that trigger escalation.
    """

    max_retries: int = DEFAULT_MAX_RETRIES
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    jitter_factor: float = 0.2
    safety_mode: str = DEFAULT_SAFETY_MODE
    escalation_threshold: int = 3


class SelfEvolutionConfig(BaseModel):
    """Layer 9 configuration for self-evolution & performance analysis.

    Attributes:
        enable: Master switch for Layer 9.
        min_turns_before_analysis: Minimum number of turns before an analysis cycle runs.
        performance_window_size: Number of recent snapshots used for trend calculation.
        auto_apply_config_delta: Whether suggested config changes are applied automatically.
    """

    enable: bool = Field(default_factory=lambda: os.getenv("SELF_EVOLUTION_ENABLE", "true").lower() == "true")
    min_turns_before_analysis: int = 1
    performance_window_size: int = 5
    auto_apply_config_delta: bool = False


class MultiAgentConfig(BaseModel):
    """Layer 10 configuration for multi-agent coordination.

    Attributes:
        enable: Master switch for Layer 10.
        max_agents: Maximum number of specialist agents allowed in a single task.
        consensus_threshold: Minimum consensus score for the synthesized result to be accepted.
        timeout_seconds: Timeout for the dispatch/aggregate cycle.
        agents: Default list of agent roles available in the registry.
        use_langgraph_backend: Whether to use the native LangGraph supervisor backend.
    """

    enable: bool = Field(default_factory=lambda: os.getenv("MULTI_AGENT_ENABLE", "true").lower() == "true")
    max_agents: int = 4
    consensus_threshold: float = 0.7
    timeout_seconds: int = 30
    agents: List[str] = Field(default_factory=lambda: ["coder", "analyst", "planner", "safety_officer"])
    use_langgraph_backend: bool = Field(
        default_factory=lambda: os.getenv("MULTI_AGENT_USE_LANGGRAPH_BACKEND", "false").lower() == "true"
    )


class SafetyGovernanceConfig(BaseModel):
    """Layer 11 configuration for safety, governance, and constitutional compliance.

    Attributes:
        enable: Master switch for Layer 11.
        audit_level: Granularity of per-turn audit (``minimal``, ``standard``, ``verbose``).
        require_governance_for: Action categories that must pass a governance vote.
        constitutional_enforcement: Whether the four constitutional mandates are enforced.
    """

    enable: bool = Field(default_factory=lambda: os.getenv("SAFETY_GOVERNANCE_ENABLE", "true").lower() == "true")
    audit_level: str = "standard"
    require_governance_for: List[str] = Field(default_factory=lambda: ["config_change", "quarantine", "escalation"])
    constitutional_enforcement: bool = True


class CognitiveImmuneConfig(BaseModel):
    """Layer 12 configuration for the cognitive immune system.

    Attributes:
        enable: Master switch for Layer 12.
        anomaly_threshold: Score above which the immune status moves to ``ALERT``.
        auto_quarantine: Whether corrupted memory entries are moved to quarantine automatically.
        auto_heal: Whether the system attempts self-healing actions after detection.
        pattern_db_ttl_seconds: TTL for entries in the in-memory threat pattern database.
        learn_enable: Whether to persist immune snapshots and compute rolling Z-score baselines.
        learn_postgres_url: PostgreSQL connection string used by the learning engine.
        learn_rolling_window: Number of recent records used for rolling statistics.
        learn_z_threshold: Z-score threshold that contributes to the learned anomaly score.
        learn_min_samples: Minimum records required before Z-score baselines are considered valid.
        learn_record_ttl_seconds: TTL for rows in the immune-history table.
    """

    enable: bool = Field(default_factory=lambda: os.getenv("COGNITIVE_IMMUNE_ENABLE", "true").lower() == "true")
    anomaly_threshold: float = 0.6
    auto_quarantine: bool = True
    auto_heal: bool = True
    pattern_db_ttl_seconds: int = 3600
    learn_enable: bool = Field(default_factory=lambda: os.getenv("COGNITIVE_IMMUNE_LEARN_ENABLE", "false").lower() == "true")
    learn_postgres_url: str = Field(default_factory=lambda: os.getenv("POSTGRES_URL", "postgresql://localhost/aio"))
    learn_rolling_window: int = 100
    learn_z_threshold: float = 2.0
    learn_min_samples: int = 10
    learn_record_ttl_seconds: int = 604800


class GovernanceDashboardConfig(BaseModel):
    """Optional governance dashboard settings.

    Attributes:
        enable: Whether the FastAPI dashboard is started automatically.
        host: Bind address for the dashboard server.
        port: Bind port for the dashboard server.
    """

    enable: bool = Field(default_factory=lambda: os.getenv("GOVERNANCE_DASHBOARD_ENABLE", "false").lower() == "true")
    host: str = Field(default_factory=lambda: os.getenv("GOVERNANCE_DASHBOARD_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("GOVERNANCE_DASHBOARD_PORT", "8050")))


class MCPServerConfig(BaseModel):
    """Single MCP server definition.

    Attributes:
        name: Human-readable server identifier.
        transport: ``stdio`` or ``sse``.
        command: Executable path when ``transport`` is ``stdio``.
        args: Command-line arguments for stdio transport.
        url: HTTP endpoint when ``transport`` is ``sse``.
        headers: Extra HTTP headers for SSE transport.
    """

    name: str
    transport: str = Field(default="stdio")
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)


class MCPConfig(BaseModel):
    """Model Context Protocol client configuration.

    Attributes:
        enable: Whether MCP discovery and tool registration are active.
        servers: List of :class:`MCPServerConfig` instances to connect on startup.
        timeout_seconds: JSON-RPC request timeout.
        auto_discover: Whether to enumerate remote tools and register them with :class:`aio.layers.tool_gate.ToolGate`.
    """

    enable: bool = Field(default_factory=lambda: DEFAULT_MCP_ENABLE)
    servers: List[MCPServerConfig] = Field(default_factory=lambda: _parse_mcp_servers_json(DEFAULT_MCP_SERVERS_JSON))
    timeout_seconds: int = DEFAULT_MCP_TIMEOUT_SECONDS
    auto_discover: bool = True


def _parse_mcp_servers_json(raw: str) -> List[MCPServerConfig]:
    import json
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [MCPServerConfig(**item) for item in data]
    except Exception:
        pass
    return []


class StreamingConfig(BaseModel):
    """Real-time cognitive streaming configuration.

    Attributes:
        enable: Master switch for the streaming subsystem.
        transport: Transport backend — ``memory``, ``sse``, or ``websocket``.
        event_persistence: ``false`` or ``redis`` for optional event replay.
        max_buffer_events: Maximum events retained in the in-memory buffer.
    """

    enable: bool = Field(default_factory=lambda: os.getenv("ENABLE_STREAMING", "false").lower() == "true")
    transport: str = Field(default_factory=lambda: os.getenv("STREAMING_TRANSPORT", "memory"))
    event_persistence: str = Field(default_factory=lambda: os.getenv("STREAMING_EVENT_PERSISTENCE", "false"))
    max_buffer_events: int = Field(default_factory=lambda: int(os.getenv("STREAMING_MAX_BUFFER_EVENTS", "1000")))


class BenchmarkConfig(BaseModel):
    """Benchmark-suite configuration.

    Attributes:
        iterations: Number of measurement iterations per scenario.
        warmup_iterations: Number of discarded warmup iterations.
        scenarios: Comma-separated list of scenario names executed by default.
        baseline_path: Path to a JSON baseline for regression detection.
        regression_threshold_percent: Percentage slowdown that triggers a regression warning.
        output_dir: Directory where benchmark reports are written.
        enable_memory_profiling: Whether RSS / peak memory is captured per run.
        enable_html_report: Whether an HTML summary is generated alongside JSON.
    """

    iterations: int = Field(default_factory=lambda: int(os.getenv("BENCHMARK_ITERATIONS", "10")))
    warmup_iterations: int = Field(default_factory=lambda: int(os.getenv("BENCHMARK_WARMUP_ITERATIONS", "2")))
    scenarios: List[str] = Field(default_factory=lambda: _parse_benchmark_scenarios(os.getenv("BENCHMARK_SCENARIOS", "echo,safety_block,failure_recovery,context_overflow,multi_agent")))
    baseline_path: Optional[str] = Field(default_factory=lambda: os.getenv("BENCHMARK_BASELINE_PATH", None))
    regression_threshold_percent: float = Field(default_factory=lambda: float(os.getenv("BENCHMARK_REGRESSION_THRESHOLD_PERCENT", "10.0")))
    output_dir: str = Field(default_factory=lambda: os.getenv("BENCHMARK_OUTPUT_DIR", "./benchmark_results"))
    enable_memory_profiling: bool = Field(default_factory=lambda: os.getenv("BENCHMARK_ENABLE_MEMORY_PROFILING", "true").lower() == "true")
    enable_html_report: bool = Field(default_factory=lambda: os.getenv("BENCHMARK_ENABLE_HTML_REPORT", "true").lower() == "true")


def _parse_benchmark_scenarios(raw: str) -> List[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


class AIOConfig(BaseModel):
    """Top-level Pydantic configuration for the entire AIO Framework.

    ``AIOConfig`` is a hierarchical composition of every layer-specific config
    model.  Each nested field can be overridden individually or via environment
    variables.  The ``enable_priority_3`` flag acts as a master switch for
    Layers 9–12 (Self-Evolution, Multi-Agent, Safety & Governance, Cognitive
    Immune System).

    Attributes:
        observability: Layer 0 — tracing, metrics, logging.
        context: Layer 1 — context-window and attention management.
        memory: Layer 2 — episodic + long-term memory backends.
        planning: Layer 3 — HiPlan, FLARE, PPA, SPIRAL, VMAO, LLM planners.
        curiosity: Layer 4 — novelty detection and intrinsic rewards.
        verifier: Layer 5 — ensemble verification and formal checks.
        tool_optimizer: Layer 6 — G-STEP, HDPO, JTPRO optimisation.
        toolgate: Layer 7 — Docker sandbox execution settings.
        failure_recovery: Layer 8 — retry, backoff, NeuroShield, escalation.
        self_evolution: Layer 9 — performance analysis and safe config changes.
        multi_agent: Layer 10 — task decomposition and consensus scoring.
        safety_governance: Layer 11 — audit, compliance, governance voting.
        cognitive_immune: Layer 12 — anomaly scanning and auto-healing.
        governance_dashboard: Optional FastAPI dashboard bindings.
        mcp: Model Context Protocol client settings.
        enable_priority_3: Global toggle for Priority 3 layers (9–12).
    """

    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    planning: PlanningConfig = Field(default_factory=PlanningConfig)
    curiosity: CuriosityConfig = Field(default_factory=CuriosityConfig)
    verifier: VerifierConfig = Field(default_factory=VerifierConfig)
    tool_optimizer: ToolOptimizerConfig = Field(default_factory=ToolOptimizerConfig)
    toolgate: ToolGateConfig = Field(default_factory=ToolGateConfig)
    failure_recovery: FailureRecoveryConfig = Field(default_factory=FailureRecoveryConfig)
    self_evolution: SelfEvolutionConfig = Field(default_factory=SelfEvolutionConfig)
    multi_agent: MultiAgentConfig = Field(default_factory=MultiAgentConfig)
    safety_governance: SafetyGovernanceConfig = Field(default_factory=SafetyGovernanceConfig)
    cognitive_immune: CognitiveImmuneConfig = Field(default_factory=CognitiveImmuneConfig)
    governance_dashboard: GovernanceDashboardConfig = Field(default_factory=GovernanceDashboardConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    streaming: StreamingConfig = Field(default_factory=StreamingConfig)
    enable_priority_3: bool = Field(default_factory=lambda: os.getenv("ENABLE_PRIORITY_3", "true").lower() == "true")
