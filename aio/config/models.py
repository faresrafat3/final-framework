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
)


class ObservabilityConfig(BaseModel):
    otel_endpoint: str = DEFAULT_OTEL_ENDPOINT
    service_name: str = DEFAULT_SERVICE_NAME
    prometheus_port: int = DEFAULT_PROMETHEUS_PORT
    log_level: str = DEFAULT_LOG_LEVEL
    enable_langsmith: bool = Field(default_factory=lambda: bool(os.getenv("LANGCHAIN_API_KEY")))
    langchain_project: str = DEFAULT_LANGCHAIN_PROJECT


class ContextConfig(BaseModel):
    max_tokens: int = 4096
    budget_reserve: int = 512
    prune_threshold: float = 0.3
    bapo_default_attention: float = 0.5


class MemoryConfig(BaseModel):
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
    novelty_threshold: float = 0.3
    intrinsic_reward_weight: float = 0.5
    serendipity_window: int = 5
    umwelt_constraints: List[str] = Field(default_factory=list)


class VerifierConfig(BaseModel):
    ensemble_threshold: float = 0.85
    formal_checks_enabled: bool = True
    llm_critique_enabled: bool = True
    debug_trace_enabled: bool = True


class ToolOptimizerConfig(BaseModel):
    gstep_threshold: float = 0.3
    hdpo_accuracy_weight: float = 0.6
    hdpo_efficiency_weight: float = 0.4
    jtpro_iterations: int = 3
    auto_deprecation_error_rate: float = 0.2


class ToolGateConfig(BaseModel):
    docker_socket: str = DEFAULT_DOCKER_SOCKET
    default_timeout_seconds: int = 30
    max_memory_mb: int = 512
    cpu_quota: int = 100000
    network_disabled: bool = True
    read_only_rootfs: bool = True
    registry_path: Optional[str] = None


class FailureRecoveryConfig(BaseModel):
    max_retries: int = DEFAULT_MAX_RETRIES
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    jitter_factor: float = 0.2
    safety_mode: str = DEFAULT_SAFETY_MODE
    escalation_threshold: int = 3


class SelfEvolutionConfig(BaseModel):
    enable: bool = Field(default_factory=lambda: os.getenv("SELF_EVOLUTION_ENABLE", "true").lower() == "true")
    min_turns_before_analysis: int = 1
    performance_window_size: int = 5
    auto_apply_config_delta: bool = False


class MultiAgentConfig(BaseModel):
    enable: bool = Field(default_factory=lambda: os.getenv("MULTI_AGENT_ENABLE", "true").lower() == "true")
    max_agents: int = 4
    consensus_threshold: float = 0.7
    timeout_seconds: int = 30
    agents: List[str] = Field(default_factory=lambda: ["coder", "analyst", "planner", "safety_officer"])


class SafetyGovernanceConfig(BaseModel):
    enable: bool = Field(default_factory=lambda: os.getenv("SAFETY_GOVERNANCE_ENABLE", "true").lower() == "true")
    audit_level: str = "standard"
    require_governance_for: List[str] = Field(default_factory=lambda: ["config_change", "quarantine", "escalation"])
    constitutional_enforcement: bool = True


class CognitiveImmuneConfig(BaseModel):
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


class AIOConfig(BaseModel):
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
    enable_priority_3: bool = Field(default_factory=lambda: os.getenv("ENABLE_PRIORITY_3", "true").lower() == "true")
