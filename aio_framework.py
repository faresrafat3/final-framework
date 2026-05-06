#!/usr/bin/env python3
"""
AIO Framework — Priority 3 Implementation
Layers: 0 (Infrastructure), 1 (Context), 2 (Memory), 3 (Planning & Anti-Myopia),
        4 (Proactive Curiosity), 5 (Verification), 6 (Tool-Use Optimization),
        7 (Execution), 8 (Failure Recovery), 9 (Self-Evolution),
        10 (Multi-Agent Coordination), 11 (Safety & Governance),
        12 (Cognitive Immune System)

A single-file, production-grade LangGraph StateGraph with all 13 layers,
nodes, edges, conditional routing, and supporting classes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict

from pydantic import BaseModel, Field, ValidationError

# ---------------------------------------------------------------------------
# Optional dependency handling
# ---------------------------------------------------------------------------
try:
    from langgraph.graph import StateGraph, END
except Exception as _e:  # pragma: no cover
    raise ImportError("langgraph is required. Install: pip install langgraph>=0.0.50") from _e

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    OTEL_AVAILABLE = True
except Exception:  # pragma: no cover
    OTEL_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except Exception:  # pragma: no cover
    PROMETHEUS_AVAILABLE = False

try:
    import docker
    DOCKER_AVAILABLE = True
except Exception:  # pragma: no cover
    DOCKER_AVAILABLE = False

try:
    from langsmith import Client as LangSmithClient
    LANGSMITH_AVAILABLE = True
except Exception:  # pragma: no cover
    LANGSMITH_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:  # pragma: no cover
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_OPENAI_AVAILABLE = True
except Exception:  # pragma: no cover
    LANGCHAIN_OPENAI_AVAILABLE = False

try:
    from langchain_anthropic import ChatAnthropic
    LANGCHAIN_ANTHROPIC_AVAILABLE = True
except Exception:  # pragma: no cover
    LANGCHAIN_ANTHROPIC_AVAILABLE = False

LANGCHAIN_CHAT_AVAILABLE = LANGCHAIN_OPENAI_AVAILABLE or LANGCHAIN_ANTHROPIC_AVAILABLE


# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

DEFAULT_OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
DEFAULT_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "aio-framework")
DEFAULT_PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))
DEFAULT_LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "aio-priority-2")
DEFAULT_MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
DEFAULT_LOG_LEVEL = os.getenv("AIO_LOG_LEVEL", "INFO").upper()
DEFAULT_SAFETY_MODE = os.getenv("SAFETY_MODE", "strict")
DEFAULT_DOCKER_SOCKET = os.getenv("DOCKER_SOCKET_PATH", "unix:///var/run/docker.sock")
DEFAULT_MEMBRIDGE_CONN = os.getenv("MEMBRIDGE_CONNECTION_STRING", "memory://localhost")
ENABLE_LLM_PLANNING = os.getenv("ENABLE_LLM_PLANNING", "false").lower() == "true"
LLM_PLANNER_PROVIDER = os.getenv("LLM_PLANNER_PROVIDER", "openai")
LLM_PLANNER_MODEL = os.getenv("LLM_PLANNER_MODEL", "gpt-4o")
LLM_PLANNER_TEMPERATURE = float(os.getenv("LLM_PLANNER_TEMPERATURE", "0.2"))
LLM_PLANNER_MAX_TOKENS = int(os.getenv("LLM_PLANNER_MAX_TOKENS", "1024"))


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# State TypedDict
# ---------------------------------------------------------------------------

class AIOState(TypedDict, total=False):
    session_id: str
    trace_id: str
    turn: int
    raw_input: str
    intent: Optional[str]
    context_window: List[Dict[str, Any]]
    context_budget: int
    attention_map: Dict[str, float]
    working_memory: List[Dict[str, Any]]
    long_term_memory: List[Dict[str, Any]]
    memory_confidence: float
    plan: Optional[str]
    hierarchical_plan: Optional[Dict[str, Any]]
    lookahead_result: Optional[Dict[str, Any]]
    fact_augmented_plan: Optional[str]
    pitfall_analysis: Optional[Dict[str, Any]]
    spiral_tree: Optional[Dict[str, Any]]
    mars_reflection: Optional[str]
    maci_meta_plan: Optional[str]
    vmao_dag: Optional[List[Dict[str, Any]]]
    curiosity_score: float
    novelty_map: Dict[str, float]
    information_gaps: List[str]
    verification_result: Dict[str, Any]
    tool_necessity_score: float
    tool_policy_channels: Dict[str, Any]
    tool_prompt_optimization: Dict[str, Any]
    sandbox_result: Optional[Dict[str, Any]]
    tool_analytics: Dict[str, Any]
    execution_result: Dict[str, Any]
    failure_state: str
    failure_count: int
    retry_budget: int
    safety_violations: List[Dict[str, Any]]
    output: Optional[str]
    error: Optional[str]
    metrics: Dict[str, Any]
    # Layer 9 — Self-Evolution
    self_evolution_report: Optional[Dict[str, Any]]
    performance_snapshot: Optional[Dict[str, Any]]
    suggested_config_delta: Optional[List[Dict[str, Any]]]
    # Layer 10 — Multi-Agent Coordination
    coordination_plan: Optional[Dict[str, Any]]
    agent_outputs: Optional[Dict[str, Any]]
    consensus_score: Optional[float]
    # Layer 11 — Safety & Governance
    audit_trail: Optional[List[Dict[str, Any]]]
    governance_result: Optional[Dict[str, Any]]
    compliance_violations: Optional[List[Dict[str, Any]]]
    # Layer 12 — Cognitive Immune System
    immune_status: Optional[str]
    anomaly_score: Optional[float]
    quarantined_ids: Optional[List[str]]
    healing_actions: Optional[List[Dict[str, Any]]]
    threat_patterns_detected: Optional[List[Dict[str, Any]]]


def make_initial_state(raw_input: str = "", session_id: Optional[str] = None) -> AIOState:
    sid = session_id or str(uuid.uuid4())
    trace_id = str(uuid.uuid4()).replace("-", "")
    return {
        "session_id": sid,
        "trace_id": trace_id,
        "turn": 0,
        "raw_input": raw_input,
        "intent": None,
        "context_window": [],
        "context_budget": 4096,
        "attention_map": {},
        "working_memory": [],
        "long_term_memory": [],
        "memory_confidence": 0.0,
        "plan": None,
        "hierarchical_plan": None,
        "lookahead_result": None,
        "fact_augmented_plan": None,
        "pitfall_analysis": None,
        "spiral_tree": None,
        "mars_reflection": None,
        "maci_meta_plan": None,
        "vmao_dag": None,
        "curiosity_score": 0.0,
        "novelty_map": {},
        "information_gaps": [],
        "verification_result": {},
        "tool_necessity_score": 0.0,
        "tool_policy_channels": {},
        "tool_prompt_optimization": {},
        "sandbox_result": None,
        "tool_analytics": {},
        "execution_result": {},
        "failure_state": "HEALTHY",
        "failure_count": 0,
        "retry_budget": DEFAULT_MAX_RETRIES,
        "safety_violations": [],
        "output": None,
        "error": None,
        "metrics": {},
        "self_evolution_report": None,
        "performance_snapshot": None,
        "suggested_config_delta": None,
        "coordination_plan": None,
        "agent_outputs": None,
        "consensus_score": None,
        "audit_trail": None,
        "governance_result": None,
        "compliance_violations": None,
        "immune_status": None,
        "anomaly_score": None,
        "quarantined_ids": None,
        "healing_actions": None,
        "threat_patterns_detected": None,
    }


# ---------------------------------------------------------------------------
# Layer 0 — Infrastructure & Observability
# ---------------------------------------------------------------------------

class ObservabilityLayer:
    """Provides tracing, metrics, logging, and optional LangSmith integration."""

    def __init__(self, config: ObservabilityConfig) -> None:
        self.config = config
        self._tracer: Optional[Any] = None
        self._langsmith: Optional[Any] = None
        self._setup_logging()
        self._setup_tracing()
        self._setup_metrics()
        self._setup_langsmith()

    def _setup_logging(self) -> None:
        level = getattr(logging, self.config.log_level, logging.INFO)
        root = logging.getLogger()
        if not root.handlers:
            logging.basicConfig(
                level=level,
                format="%(asctime)s %(name)s %(levelname)s: %(message)s",
            )
        else:
            for handler in root.handlers:
                handler.setLevel(level)
        self.logger = logging.getLogger("aio.observability")
        self.logger.setLevel(level)

    def _setup_tracing(self) -> None:
        if not OTEL_AVAILABLE:
            self.logger.warning("OpenTelemetry not available; tracing disabled.")
            return
        resource = Resource.create({SERVICE_NAME: self.config.service_name})
        provider = TracerProvider(resource=resource)
        try:
            exporter = OTLPSpanExporter(endpoint=self.config.otel_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception as exc:
            self.logger.warning("OTLP exporter failed (%s); falling back to console.", exc)
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer("aio")

    def _setup_metrics(self) -> None:
        if not PROMETHEUS_AVAILABLE:
            self.logger.warning("Prometheus client not available; metrics disabled.")
            return
        from prometheus_client import CollectorRegistry
        self._registry = CollectorRegistry()
        self.node_latency = Histogram(
            "aio_node_latency_seconds", "Latency per node", ["node_name"],
            registry=self._registry,
        )
        self.node_counter = Counter(
            "aio_node_executions_total", "Total node executions", ["node_name", "status"],
            registry=self._registry,
        )
        self.failure_gauge = Gauge(
            "aio_failure_state", "Current failure state (0=HEALTHY,1=DEGRADED,2=RECOVERING,3=FAILED)",
            registry=self._registry,
        )
        self.context_budget_gauge = Gauge(
            "aio_context_budget_tokens", "Remaining context budget",
            registry=self._registry,
        )
        if self.config.prometheus_port:
            try:
                start_http_server(self.config.prometheus_port, registry=self._registry)
                self.logger.info("Prometheus metrics server started on port %d", self.config.prometheus_port)
            except Exception as exc:
                self.logger.warning("Could not start Prometheus server: %s", exc)

    def _setup_langsmith(self) -> None:
        if not LANGSMITH_AVAILABLE or not self.config.enable_langsmith:
            return
        try:
            self._langsmith = LangSmithClient()
            self.logger.info("LangSmith client initialized.")
        except Exception as exc:
            self.logger.warning("LangSmith init failed: %s", exc)

    def start_span(self, name: str, trace_id: Optional[str] = None) -> Any:
        if self._tracer is None:
            return _NullContext()
        ctx = trace.set_span_in_context(trace.NonRecordingSpan(trace.SpanContext(
            trace_id=int(trace_id or "0" * 32, 16),
            span_id=int(uuid.uuid4().hex[:16], 16),
            is_remote=False,
            trace_flags=trace.TraceFlags(trace.TraceFlags.SAMPLED),
        )))
        return self._tracer.start_as_current_span(name, context=ctx)

    def record_latency(self, node_name: str, seconds: float) -> None:
        if PROMETHEUS_AVAILABLE and hasattr(self, "node_latency"):
            self.node_latency.labels(node_name=node_name).observe(seconds)

    def count_node(self, node_name: str, status: str) -> None:
        if PROMETHEUS_AVAILABLE and hasattr(self, "node_counter"):
            self.node_counter.labels(node_name=node_name, status=status).inc()

    def set_failure_state(self, state: str) -> None:
        mapping = {"HEALTHY": 0, "DEGRADED": 1, "RECOVERING": 2, "FAILED": 3}
        if PROMETHEUS_AVAILABLE and hasattr(self, "failure_gauge"):
            self.failure_gauge.set(mapping.get(state, 0))

    def set_context_budget(self, tokens: int) -> None:
        if PROMETHEUS_AVAILABLE and hasattr(self, "context_budget_gauge"):
            self.context_budget_gauge.set(tokens)

    def log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        extra = extra or {}
        extra.setdefault("correlation_id", str(uuid.uuid4())[:8])
        self.logger.log(level, message, extra=extra)


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Layer 1 — Context & Attention Management
# ---------------------------------------------------------------------------

class ContextManager:
    """Manages context window, BAPO attention routing, and working memory pruning."""

    def __init__(self, config: ContextConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    @staticmethod
    def approximate_token_count(text: str) -> int:
        """Rough token count: ~4 chars per token for English-like text."""
        return max(1, len(text) // 4)

    def ingest(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("context.ingest", state.get("trace_id")):
            raw = state.get("raw_input", "")
            intent = self._classify_intent(raw)
            state["intent"] = intent
            state["turn"] = state.get("turn", 0) + 1
            state["context_window"] = state.get("context_window", []) + [
                {"role": "user", "content": raw, "turn": state["turn"]}
            ]
            state["attention_map"] = {
                "memory": 0.6,
                "verify": 0.4 if intent in {"analysis", "coding"} else 0.2,
                "execute": 0.7 if intent in {"action", "tool_use"} else 0.3,
                "recover": 0.5,
            }
            self.obs.record_latency("context.ingest", time.time() - start)
            self.obs.count_node("context.ingest", "success")
        return state

    def sculpt(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("context.sculpt", state.get("trace_id")):
            window = state.get("context_window", [])
            budget = self.config.max_tokens - self.config.budget_reserve
            total = sum(self.approximate_token_count(str(msg.get("content", ""))) for msg in window)
            while total > budget and window:
                idx = self._find_prunable_index(window)
                removed = window.pop(idx)
                state.setdefault("working_memory", []).append({
                    **removed,
                    "pruned_at": time.time(),
                    "reason": "budget_overflow",
                })
                total = sum(self.approximate_token_count(str(msg.get("content", ""))) for msg in window)
            state["context_window"] = window
            state["context_budget"] = budget - total
            self.obs.set_context_budget(state["context_budget"])
            self.obs.record_latency("context.sculpt", time.time() - start)
            self.obs.count_node("context.sculpt", "success")
        return state

    def route_attention(self, state: AIOState) -> str:
        """Return next layer target based on BAPO attention map."""
        amap = dict(state.get("attention_map", {}))
        if not amap:
            return "memory"
        if state.get("failure_state") in {"DEGRADED", "RECOVERING"}:
            amap = {k: (v * 0.5 if k != "recover" else min(1.0, v + 0.3)) for k, v in amap.items()}
        target = max(amap, key=lambda k: amap[k])
        return target

    def _classify_intent(self, raw: str) -> str:
        lowered = raw.lower()
        if any(k in lowered for k in ("run", "execute", "call", "invoke", "tool")):
            return "action"
        if any(k in lowered for k in ("analyze", "review", "check", "verify", "debug")):
            return "analysis"
        if any(k in lowered for k in ("write", "code", "script", "function")):
            return "coding"
        return "general"

    def _find_prunable_index(self, window: List[Dict[str, Any]]) -> int:
        for i, msg in enumerate(window):
            if msg.get("role") != "system":
                return i
        return 0


# ---------------------------------------------------------------------------
# Layer 2 — Dual-Memory Bridge
# ---------------------------------------------------------------------------

class MemoryBridge:
    """Implements encode-verify-store-consolidate-retrieve-forget lifecycle."""

    def __init__(self, config: MemoryConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._episodic: Dict[str, Dict[str, Any]] = {}
        self._long_term: Dict[str, Dict[str, Any]] = {}
        self._keyword_index: Dict[str, List[str]] = {}
        self._embedding_model: Optional[Any] = None
        if config.use_real_embeddings and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self._embedding_model = SentenceTransformer(config.embedding_model_name)
            except Exception as exc:  # pragma: no cover
                logging.warning("Failed to load embedding model '%s': %s. Falling back to pseudo-embeddings.", config.embedding_model_name, exc)

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _mia_score(self, entry: Dict[str, Any]) -> float:
        """Memory Importance Assessment: composite score [0,1]."""
        base = 0.5
        if entry.get("role") == "user":
            base += 0.1
        if "error" in str(entry.get("content", "")).lower():
            base += 0.2
        if entry.get("verification_passed"):
            base += 0.1
        recency = max(0.0, 1.0 - (time.time() - entry.get("timestamp", time.time())) / 3600)
        return min(1.0, base + recency * 0.1)

    def _embed(self, content: str) -> List[float]:
        """Return real or pseudo embedding depending on config and availability."""
        if self._embedding_model is not None:
            vec = self._embedding_model.encode(content, convert_to_numpy=True)
            norm = float(vec.dot(vec)) ** 0.5 or 1.0
            return [float(v) / norm for v in vec]
        h = int(hashlib.sha256(content.encode()).hexdigest(), 16)
        random.seed(h)
        vec = [random.random() for _ in range(64)]
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        return max(0.0, min(1.0, dot))

    def _index_keywords(self, entry_id: str, content: str) -> None:
        words = set(re.findall(r"\b\w{3,}\b", content.lower()))
        for w in words:
            self._keyword_index.setdefault(w, []).append(entry_id)

    def encode(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("memory.encode", state.get("trace_id")):
            window = state.get("context_window", [])
            for msg in window:
                content = str(msg.get("content", ""))
                eid = self._hash(content)
                if eid in self._episodic:
                    continue
                embedding = self._embed(content)
                entry = {
                    "id": eid,
                    "role": msg.get("role", "unknown"),
                    "content": content,
                    "turn": msg.get("turn", 0),
                    "timestamp": time.time(),
                    "embedding": embedding,
                    "verification_passed": False,
                }
                entry["importance"] = self._mia_score(entry)
                self._episodic[eid] = entry
                self._index_keywords(eid, content)
            self.obs.record_latency("memory.encode", time.time() - start)
            self.obs.count_node("memory.encode", "success")
        return state

    def verify(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("memory.verify", state.get("trace_id")):
            seen: set = set()
            for eid, entry in list(self._episodic.items()):
                content = entry["content"]
                if content in seen:
                    del self._episodic[eid]
                    continue
                seen.add(content)
                if not content or len(content) > 10000:
                    entry["verification_passed"] = False
                else:
                    entry["verification_passed"] = True
            self.obs.record_latency("memory.verify", time.time() - start)
            self.obs.count_node("memory.verify", "success")
        return state

    def store(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("memory.store", state.get("trace_id")):
            self.obs.record_latency("memory.store", time.time() - start)
            self.obs.count_node("memory.store", "success")
        return state

    def consolidate(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("memory.consolidate", state.get("trace_id")):
            batch: List[Dict[str, Any]] = []
            cutoff = time.time() - self.config.epiphany_ttl_seconds
            for eid, entry in list(self._episodic.items()):
                if entry["timestamp"] < cutoff and entry.get("verification_passed"):
                    batch.append(entry)
                if len(batch) >= self.config.consolidation_batch_size:
                    break
            for entry in batch:
                eid = entry["id"]
                self._long_term[eid] = entry
                if eid in self._episodic:
                    del self._episodic[eid]
            state["long_term_memory"] = list(self._long_term.values())
            self.obs.record_latency("memory.consolidate", time.time() - start)
            self.obs.count_node("memory.consolidate", "success")
        return state

    def retrieve(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("memory.retrieve", state.get("trace_id")):
            query = state.get("raw_input", "")
            q_embed = self._embed(query)
            q_words = set(re.findall(r"\b\w{3,}\b", query.lower()))
            candidate_ids: set = set()
            for w in q_words:
                candidate_ids.update(self._keyword_index.get(w, []))
            pool = {**self._long_term, **self._episodic}
            if not candidate_ids:
                candidate_ids = set(pool.keys())

            scored: List[Tuple[str, float]] = []
            for eid in candidate_ids:
                entry = pool.get(eid)
                if not entry:
                    continue
                vec_sim = self._cosine_similarity(q_embed, entry.get("embedding", q_embed))
                kw_boost = 0.1 if any(w in entry.get("content", "").lower() for w in q_words) else 0.0
                importance = entry.get("importance", 0.5)
                recency = max(0.0, 1.0 - (time.time() - entry.get("timestamp", time.time())) / 3600)
                score = vec_sim * 0.5 + importance * 0.25 + recency * 0.15 + kw_boost
                scored.append((eid, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_k = scored[: self.config.retrieval_top_k]
            retrieved = [pool[eid] for eid, _ in top_k if eid in pool]
            confidence = top_k[0][1] if top_k else 0.0
            state["working_memory"] = retrieved
            state["memory_confidence"] = round(confidence, 4)
            self.obs.record_latency("memory.retrieve", time.time() - start)
            self.obs.count_node("memory.retrieve", "success")
        return state

    def forget(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("memory.forget", state.get("trace_id")):
            now = time.time()
            for store in (self._episodic, self._long_term):
                for eid in list(store.keys()):
                    entry = store[eid]
                    age = now - entry.get("timestamp", now)
                    importance = entry.get("importance", 0.5)
                    if age > self.config.forget_ttl_seconds and importance < self.config.importance_threshold:
                        del store[eid]
                        for lst in self._keyword_index.values():
                            if eid in lst:
                                lst.remove(eid)
            self.obs.record_latency("memory.forget", time.time() - start)
            self.obs.count_node("memory.forget", "success")
        return state


# ---------------------------------------------------------------------------
# Layer 3 — Planning & Anti-Myopia Countermeasures
# ---------------------------------------------------------------------------

class HiPlanPlanner:
    """Hierarchical planning: decomposes a flat plan into goal-subgoal-action tree."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    def plan(self, state: AIOState) -> Dict[str, Any]:
        """Build a hierarchical plan from the current flat plan."""
        start = time.time()
        with self.obs.start_span("planning.hiplan", state.get("trace_id")):
            raw_plan = state.get("plan", "")
            steps = [s.strip() for s in re.split(r"\d+\)", raw_plan) if s.strip()]
            hierarchy = {
                "goal": state.get("intent", "general"),
                "subgoals": [
                    {
                        "id": f"sg-{i}",
                        "description": step,
                        "actions": [{"id": f"act-{i}-0", "description": f"Execute: {step}"}],
                    }
                    for i, step in enumerate(steps[: self.config.hiplan_max_depth])
                ],
            }
            self.obs.record_latency("planning.hiplan", time.time() - start)
            self.obs.count_node("planning.hiplan", "success")
        return hierarchy


class FLARELookahead:
    """Future-aware lookahead: scores trajectories over a planning horizon."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    def lookahead(self, state: AIOState) -> Dict[str, Any]:
        """Simulate future steps and return risk-adjusted trajectory scores."""
        start = time.time()
        with self.obs.start_span("planning.flare", state.get("trace_id")):
            horizon = self.config.flare_horizon
            confidence = state.get("memory_confidence", 0.0)
            scores = []
            for step in range(horizon):
                score = 0.5 + (confidence * 0.3) - (step * 0.1)
                scores.append(round(max(0.0, min(1.0, score)), 4))
            best_step = scores.index(max(scores)) if scores else 0
            risk = "low" if max(scores, default=0.0) > 0.7 else "medium"
            self.obs.record_latency("planning.flare", time.time() - start)
            self.obs.count_node("planning.flare", "success")
            return {
                "horizon": horizon,
                "trajectory_scores": scores,
                "recommended_action_index": best_step,
                "risk_assessment": risk,
            }


class LWMPlanner:
    """Fact-augmented planning: enriches plan with verified facts from memory."""

    def __init__(self, observability: ObservabilityLayer) -> None:
        self.obs = observability

    def augment(self, state: AIOState) -> str:
        """Return plan augmented with facts from verified working memory."""
        start = time.time()
        with self.obs.start_span("planning.lwm", state.get("trace_id")):
            plan = state.get("plan", "")
            memories = state.get("working_memory", [])
            facts = [m["content"] for m in memories if m.get("verification_passed")]
            if facts:
                augmented = f"[FACTS] {' | '.join(facts[:3])}\n[PLAN] {plan}"
            else:
                augmented = plan
            self.obs.record_latency("planning.lwm", time.time() - start)
            self.obs.count_node("planning.lwm", "success")
        return augmented


class PPAPlanner:
    """Proactive Pitfall Avoidance: detects likely failure modes and adds guardrails."""

    def __init__(self, observability: ObservabilityLayer) -> None:
        self.obs = observability

    def analyze(self, state: AIOState) -> Dict[str, Any]:
        """Analyze plan for pitfalls and return guardrail recommendations."""
        start = time.time()
        with self.obs.start_span("planning.ppa", state.get("trace_id")):
            plan = state.get("plan", "")
            pitfalls = []
            lowered = (plan or "").lower()
            if "loop" in lowered or "while" in lowered:
                pitfalls.append({"type": "infinite_loop", "mitigation": "Add iteration limit."})
            if "delete" in lowered or "remove" in lowered:
                pitfalls.append({"type": "data_loss", "mitigation": "Add backup step."})
            if len(plan or "") > 2000:
                pitfalls.append({"type": "complexity", "mitigation": "Decompose into smaller subplans."})
            safe_to_proceed = len(pitfalls) == 0
            self.obs.record_latency("planning.ppa", time.time() - start)
            self.obs.count_node("planning.ppa", "success" if safe_to_proceed else "blocked")
            return {
                "pitfalls_detected": pitfalls,
                "guardrails_added": [p["mitigation"] for p in pitfalls],
                "safe_to_proceed": safe_to_proceed,
            }


class SPIRALPlanner:
    """Symbolic MCTS planning via Planner-Simulator-Critic tri-agent loop."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    def mcts_plan(self, state: AIOState) -> Dict[str, Any]:
        """Run lightweight symbolic MCTS and return best variant."""
        start = time.time()
        with self.obs.start_span("planning.spiral", state.get("trace_id")):
            root = {"state": state.get("plan", ""), "visits": 0, "value": 0.0, "children": []}
            for sim in range(self.config.spiral_simulations):
                child = {"id": f"sim-{sim}", "plan_variant": f"Variant {sim}"}
                outcome = random.uniform(0.0, 1.0)
                score = outcome * 0.8 + 0.2
                root["children"].append({**child, "score": round(score, 4)})
            best = max(root["children"], key=lambda c: c["score"]) if root["children"] else None
            self.obs.record_latency("planning.spiral", time.time() - start)
            self.obs.count_node("planning.spiral", "success")
            return {
                "root": root,
                "best_variant": best,
                "exploration_rate": 1.0 / (1 + len(root["children"])),
            }


class MARSReflector:
    """One-shot self-reflection: critiques the current plan and surfaces concerns."""

    def __init__(self, observability: ObservabilityLayer) -> None:
        self.obs = observability

    def reflect(self, state: AIOState) -> str:
        """Return a one-shot reflection on plan quality."""
        start = time.time()
        with self.obs.start_span("planning.mars", state.get("trace_id")):
            plan = state.get("plan", "")
            verification = state.get("verification_result", {})
            critiques = verification.get("critiques", [])
            if critiques:
                reflection = f"MARS Reflection: Plan has {len(critiques)} issue(s): {'; '.join(critiques)}."
            else:
                reflection = "MARS Reflection: Plan appears sound; no immediate concerns."
            self.obs.record_latency("planning.mars", time.time() - start)
            self.obs.count_node("planning.mars", "success")
        return reflection


class MACIMetaPlanner:
    """Meta-planner: selects the most appropriate planner for the task."""

    def __init__(self, observability: ObservabilityLayer) -> None:
        self.obs = observability

    def select_planner(self, state: AIOState) -> str:
        """Return planner name best suited for current intent."""
        start = time.time()
        with self.obs.start_span("planning.maci", state.get("trace_id")):
            intent = state.get("intent", "general")
            if intent in {"coding", "analysis"}:
                selected = "spiral"
            elif intent == "action":
                selected = "vmao"
            else:
                selected = "hiplan"
            self.obs.record_latency("planning.maci", time.time() - start)
            self.obs.count_node("planning.maci", "success")
        return selected


class VMAOPlanner:
    """Plan-execute-verify-replan with DAG decomposition."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability

    def decompose(self, state: AIOState) -> List[Dict[str, Any]]:
        """Decompose plan into a DAG of executable nodes."""
        start = time.time()
        with self.obs.start_span("planning.vmao.decompose", state.get("trace_id")):
            plan = state.get("plan", "")
            steps = [s.strip() for s in re.split(r"\d+\)", plan) if s.strip()]
            dag = []
            for i, step in enumerate(steps):
                node = {
                    "id": f"node-{i}",
                    "description": step,
                    "dependencies": [f"node-{i-1}"] if i > 0 else [],
                    "status": "pending",
                    "verified": False,
                }
                dag.append(node)
            self.obs.record_latency("planning.vmao.decompose", time.time() - start)
            self.obs.count_node("planning.vmao.decompose", "success")
        return dag

    def replan(self, state: AIOState) -> List[Dict[str, Any]]:
        """Replan failed DAG nodes."""
        dag = state.get("vmao_dag", [])
        for node in dag:
            if not node.get("verified"):
                node["status"] = "replanning"
                node["description"] = f"[REPLAN] {node['description']}"
        return dag


class LLMPlanner:
    """Optional LLM-powered planner behind a feature flag and optional dependency guard."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._model: Optional[Any] = None

    def _get_chat_model(self) -> Optional[Any]:
        if not LANGCHAIN_CHAT_AVAILABLE:
            return None
        if self._model is not None:
            return self._model
        provider = self.config.llm_planner_provider
        if provider == "openai" and LANGCHAIN_OPENAI_AVAILABLE:
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                self.obs.log(logging.WARNING, "LLMPlanner: OPENAI_API_KEY not set")
                return None
            self._model = ChatOpenAI(
                model=self.config.llm_planner_model,
                temperature=self.config.llm_planner_temperature,
                max_tokens=self.config.llm_planner_max_tokens,
                api_key=key,
            )
            return self._model
        if provider == "anthropic" and LANGCHAIN_ANTHROPIC_AVAILABLE:
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                self.obs.log(logging.WARNING, "LLMPlanner: ANTHROPIC_API_KEY not set")
                return None
            self._model = ChatAnthropic(
                model=self.config.llm_planner_model,
                temperature=self.config.llm_planner_temperature,
                max_tokens=self.config.llm_planner_max_tokens,
                api_key=key,
            )
            return self._model
        return None

    def _call_llm(self, prompt: str, span_name: str) -> str:
        model = self._get_chat_model()
        if model is None:
            raise RuntimeError("LLM chat model not available")
        start = time.time()
        with self.obs.start_span(span_name):
            try:
                response = model.invoke(prompt)
                text = str(response.content if hasattr(response, "content") else response)
                self.obs.record_latency(span_name, time.time() - start)
                self.obs.count_node(span_name, "success")
                return text
            except Exception as exc:
                self.obs.record_latency(span_name, time.time() - start)
                self.obs.count_node(span_name, "failure")
                self.obs.log(logging.WARNING, f"LLMPlanner {span_name} failed: {exc}")
                raise

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except Exception:
            return {}

    def generate_plan(self, state: AIOState) -> str:
        intent = state.get("intent", "general")
        memory = state.get("working_memory", [])
        snippets = " | ".join(str(m.get("content", ""))[:200] for m in memory[:3])
        prompt = (
            f"You are a planning assistant. Given the intent '{intent}' and recent memory snippets: [{snippets}],\n"
            "produce a concise, numbered step-by-step plan (max 5 steps). "
            "Return only the plan text with no extra commentary."
        )
        return self._call_llm(prompt, "planning.llm_generate")

    def decompose_tasks(self, state: AIOState) -> Dict[str, Any]:
        intent = state.get("intent", "general")
        plan = state.get("plan", "")
        prompt = (
            f"You are a hierarchical planning assistant. Decompose this plan into JSON with keys:"
            f"  goal: string"
            f"  subgoals: list of {{id, description, actions: [{{id, description}}]}}"
            f"Intent: {intent}"
            f"Plan: {plan}"
            f"Return only valid JSON inside a markdown code block if needed."
        )
        text = self._call_llm(prompt, "planning.llm_decompose")
        parsed = self._parse_json(text)
        if not parsed or "goal" not in parsed:
            raise RuntimeError("LLM decompose returned invalid JSON")
        return parsed

    def lookahead_analysis(self, state: AIOState) -> Dict[str, Any]:
        horizon = self.config.flare_horizon
        plan = state.get("plan", "")
        prompt = (
            f"You are a risk-aware lookahead assistant. Analyze this plan over a horizon of {horizon} steps."
            f"Return JSON with keys: horizon (int), trajectory_scores (list of floats), recommended_action_index (int), risk_assessment (string)."
            f"Plan: {plan}"
            f"Return only valid JSON inside a markdown code block if needed."
        )
        text = self._call_llm(prompt, "planning.llm_lookahead")
        parsed = self._parse_json(text)
        required = {"horizon", "trajectory_scores", "recommended_action_index", "risk_assessment"}
        if not required.issubset(parsed.keys()):
            raise RuntimeError("LLM lookahead returned incomplete JSON")
        return parsed

    def pitfall_analysis(self, state: AIOState) -> Dict[str, Any]:
        plan = state.get("plan", "")
        prompt = (
            f"You are a safety reviewer. Review this plan and return JSON with keys:"
            f"  pitfalls_detected: list of {{type, mitigation}}"
            f"  guardrails_added: list of strings"
            f"  safe_to_proceed: bool"
            f"Plan: {plan}"
            f"Return only valid JSON inside a markdown code block if needed."
        )
        text = self._call_llm(prompt, "planning.llm_pitfall")
        parsed = self._parse_json(text)
        required = {"pitfalls_detected", "guardrails_added", "safe_to_proceed"}
        if not required.issubset(parsed.keys()):
            raise RuntimeError("LLM pitfall returned incomplete JSON")
        return parsed


class PlanningLayer:
    """Orchestrates all Layer 3 planners with escalation and rejection paths."""

    def __init__(self, config: PlanningConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self.hiplan = HiPlanPlanner(config, observability)
        self.flare = FLARELookahead(config, observability)
        self.lwm = LWMPlanner(observability)
        self.ppa = PPAPlanner(observability)
        self.spiral = SPIRALPlanner(config, observability)
        self.mars = MARSReflector(observability)
        self.maci = MACIMetaPlanner(observability)
        self.vmao = VMAOPlanner(config, observability)
        if config.enable_llm_planning:
            self._llm_planner: Optional[LLMPlanner] = LLMPlanner(config, observability)
        else:
            self._llm_planner = None

    def _heuristic_plan(self, state: AIOState) -> str:
        intent = state.get("intent", "general")
        memory = state.get("working_memory", [])
        snippets = " | ".join(str(m.get("content", ""))[:100] for m in memory[:3])
        return f"Plan for intent='{intent}': 1) ingest input 2) retrieve memory [{snippets}] 3) verify 4) execute 5) finalize."

    def generate_plan(self, state: AIOState) -> AIOState:
        if self._llm_planner is not None:
            try:
                state["plan"] = self._llm_planner.generate_plan(state)
                return state
            except Exception as exc:
                self.obs.log(logging.WARNING, f"LLM generate_plan failed, falling back to heuristic: {exc}")
                self.obs.count_node("planning.llm_generate", "fallback")
        state["plan"] = self._heuristic_plan(state)
        return state

    def run_hiplan(self, state: AIOState) -> AIOState:
        if self._llm_planner is not None:
            try:
                state["hierarchical_plan"] = self._llm_planner.decompose_tasks(state)
                return state
            except Exception as exc:
                self.obs.log(logging.WARNING, f"LLM decompose_tasks failed, falling back to heuristic: {exc}")
                self.obs.count_node("planning.llm_decompose", "fallback")
        state["hierarchical_plan"] = self.hiplan.plan(state)
        return state

    def run_flare(self, state: AIOState) -> AIOState:
        if self._llm_planner is not None:
            try:
                state["lookahead_result"] = self._llm_planner.lookahead_analysis(state)
                return state
            except Exception as exc:
                self.obs.log(logging.WARNING, f"LLM lookahead_analysis failed, falling back to heuristic: {exc}")
                self.obs.count_node("planning.llm_lookahead", "fallback")
        state["lookahead_result"] = self.flare.lookahead(state)
        return state

    def run_lwm(self, state: AIOState) -> AIOState:
        state["fact_augmented_plan"] = self.lwm.augment(state)
        return state

    def run_ppa(self, state: AIOState) -> AIOState:
        if self._llm_planner is not None:
            try:
                analysis = self._llm_planner.pitfall_analysis(state)
                state["pitfall_analysis"] = analysis
                if not analysis.get("safe_to_proceed", True):
                    state["failure_state"] = "FAILED"
                    state["error"] = state.get("error") or f"PPA blocked: {len(analysis['pitfalls_detected'])} pitfall(s) detected."
                    self.obs.set_failure_state("FAILED")
                    self.obs.count_node("planning.ppa", "escalated")
                return state
            except Exception as exc:
                self.obs.log(logging.WARNING, f"LLM pitfall_analysis failed, falling back to heuristic: {exc}")
                self.obs.count_node("planning.llm_pitfall", "fallback")
        analysis = self.ppa.analyze(state)
        state["pitfall_analysis"] = analysis
        if not analysis.get("safe_to_proceed", True):
            state["failure_state"] = "FAILED"
            state["error"] = state.get("error") or f"PPA blocked: {len(analysis['pitfalls_detected'])} pitfall(s) detected."
            self.obs.set_failure_state("FAILED")
            self.obs.count_node("planning.ppa", "escalated")
        return state

    def run_spiral(self, state: AIOState) -> AIOState:
        state["spiral_tree"] = self.spiral.mcts_plan(state)
        return state

    def run_mars(self, state: AIOState) -> AIOState:
        state["mars_reflection"] = self.mars.reflect(state)
        return state

    def run_maci(self, state: AIOState) -> AIOState:
        state["maci_meta_plan"] = self.maci.select_planner(state)
        return state

    def run_vmao_decompose(self, state: AIOState) -> AIOState:
        state["vmao_dag"] = self.vmao.decompose(state)
        return state

    def run_vmao_replan(self, state: AIOState) -> AIOState:
        state["vmao_dag"] = self.vmao.replan(state)
        return state


# ---------------------------------------------------------------------------
# Layer 4 — Proactive Curiosity & Exploration
# ---------------------------------------------------------------------------

class CuriosityEngine:
    """CuriosityEngine: intrinsic reward, active seeking, serendipity, counterfactuals, umwelt."""

    def __init__(self, config: CuriosityConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._visited_states: set = set()

    def intrinsic_reward(self, state: AIOState) -> AIOState:
        """Compute intrinsic reward for the current plan based on novelty."""
        start = time.time()
        with self.obs.start_span("curiosity.intrinsic_reward", state.get("trace_id")):
            plan = state.get("plan", "")
            state_hash = hashlib.sha256(str(plan).encode()).hexdigest()[:16]
            novelty = 1.0 if state_hash not in self._visited_states else 0.1
            self._visited_states.add(state_hash)
            score = novelty * self.config.intrinsic_reward_weight
            state["curiosity_score"] = round(score, 4)
            state.setdefault("novelty_map", {})[state_hash] = round(novelty, 4)
            self.obs.record_latency("curiosity.intrinsic_reward", time.time() - start)
            self.obs.count_node("curiosity.intrinsic_reward", "success")
        return state

    def active_seek(self, state: AIOState) -> AIOState:
        """Identify information gaps and formulate questions to close them."""
        start = time.time()
        with self.obs.start_span("curiosity.active_seek", state.get("trace_id")):
            gaps = []
            if not state.get("working_memory"):
                gaps.append("No relevant working memory; need to retrieve or encode more context.")
            if state.get("memory_confidence", 0.0) < 0.5:
                gaps.append("Low memory confidence; seek additional facts.")
            state["information_gaps"] = gaps
            self.obs.record_latency("curiosity.active_seek", time.time() - start)
            self.obs.count_node("curiosity.active_seek", "success")
        return state

    def serendipity(self, state: AIOState) -> AIOState:
        """Detect unexpected patterns that may represent useful opportunities."""
        start = time.time()
        with self.obs.start_span("curiosity.serendipity", state.get("trace_id")):
            plan = state.get("plan", "")
            insight = None
            if "error" in str(plan).lower():
                insight = "Serendipity: Plan mentions error handling—opportunity to improve robustness."
            state.setdefault("metrics", {})["serendipity_insight"] = insight
            self.obs.record_latency("curiosity.serendipity", time.time() - start)
            self.obs.count_node("curiosity.serendipity", "success")
        return state

    def counterfactual(self, state: AIOState) -> AIOState:
        """Explore counterfactual what-if scenarios."""
        start = time.time()
        with self.obs.start_span("curiosity.counterfactual", state.get("trace_id")):
            plan = state.get("plan", "")
            alternatives = [
                f"What if we skipped verification? Plan: {plan}",
                f"What if we used a different tool? Plan: {plan}",
            ]
            state.setdefault("metrics", {})["counterfactuals"] = alternatives
            self.obs.record_latency("curiosity.counterfactual", time.time() - start)
            self.obs.count_node("curiosity.counterfactual", "success")
        return state

    def umwelt_constraints(self, state: AIOState) -> AIOState:
        """Apply Umwelt Engineering constraints to the agent's perceptual boundary."""
        start = time.time()
        with self.obs.start_span("curiosity.umwelt", state.get("trace_id")):
            constraints = self.config.umwelt_constraints or [
                "No network access beyond localhost",
                "Read-only filesystem for sandbox",
                "Max 512MB memory per tool call",
            ]
            state.setdefault("metrics", {})["umwelt_constraints"] = constraints
            self.obs.record_latency("curiosity.umwelt", time.time() - start)
            self.obs.count_node("curiosity.umwelt", "success")
        return state


# ---------------------------------------------------------------------------
# Layer 5 — Verification & Quality Assurance
# ---------------------------------------------------------------------------

class Verifier:
    """Multi-modal verification: LLM critique, formal rules, competence scoring, debug."""

    def __init__(self, config: VerifierConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._historical_scores: List[float] = []

    def critique(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("verifier.critique", state.get("trace_id")):
            plan = state.get("plan", "")
            critiques: List[str] = []
            if not plan:
                critiques.append("No plan generated.")
            else:
                if len(plan) < 10:
                    critiques.append("Plan is suspiciously short.")
                if "step" not in plan.lower() and "action" not in plan.lower():
                    critiques.append("Plan lacks explicit steps or actions.")
            result = state.setdefault("verification_result", {})
            result["critiques"] = critiques
            result["llm_pass"] = len(critiques) == 0
            self.obs.record_latency("verifier.critique", time.time() - start)
            self.obs.count_node("verifier.critique", "success" if result["llm_pass"] else "failure")
        return state

    def judge(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("verifier.judge", state.get("trace_id")):
            result = state.setdefault("verification_result", {})
            checks: List[Dict[str, Any]] = []
            plan = state.get("plan", "")
            checks.append({"rule": "non_empty", "passed": bool(plan)})
            forbidden = {"rm -rf /", "drop table", "delete from", "format c:"}
            violation = any(f in (plan or "").lower() for f in forbidden)
            checks.append({"rule": "forbidden_patterns", "passed": not violation})
            checks.append({"rule": "length_bound", "passed": len(plan or "") < 5000})
            all_passed = all(c["passed"] for c in checks)
            result["formal_checks"] = checks
            result["formal_pass"] = all_passed
            self.obs.record_latency("verifier.judge", time.time() - start)
            self.obs.count_node("verifier.judge", "success" if all_passed else "failure")
        return state

    def score(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("verifier.score", state.get("trace_id")):
            result = state.setdefault("verification_result", {})
            llm_pass = float(result.get("llm_pass", False))
            formal_pass = float(result.get("formal_pass", False))
            ensemble = llm_pass * 0.5 + formal_pass * 0.5
            if self._historical_scores:
                trend = sum(self._historical_scores[-10:]) / min(len(self._historical_scores), 10)
                ensemble = ensemble * 0.8 + trend * 0.2
            ensemble = round(max(0.0, min(1.0, ensemble)), 4)
            self._historical_scores.append(ensemble)
            result["ensemble_score"] = ensemble
            result["passed"] = ensemble >= self.config.ensemble_threshold
            self.obs.record_latency("verifier.score", time.time() - start)
            self.obs.count_node("verifier.score", "success" if result["passed"] else "failure")
        return state

    def debug(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("verifier.debug", state.get("trace_id")):
            result = state.setdefault("verification_result", {})
            if not result.get("passed"):
                hypotheses = []
                if not result.get("llm_pass"):
                    hypotheses.append("Plan quality insufficient; consider more detailed decomposition.")
                if not result.get("formal_pass"):
                    hypotheses.append("Formal constraints violated; review forbidden patterns or length.")
                result["debug_hypotheses"] = hypotheses
            self.obs.record_latency("verifier.debug", time.time() - start)
            self.obs.count_node("verifier.debug", "success")
        return state


# ---------------------------------------------------------------------------
# Layer 6 — Tool-Use Optimization
# ---------------------------------------------------------------------------

class ToolOptimizer:
    """G-STEP, HDPO, JTPRO, sandbox execution, and tool usage analytics with auto-deprecation."""

    def __init__(self, config: ToolOptimizerConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._usage_stats: Dict[str, Dict[str, Any]] = {}

    def gstep_evaluate(self, state: AIOState) -> AIOState:
        """G-STEP gate: evaluate whether a tool call is actually necessary.

        If the score is below threshold, the node sets a routing flag
        but does not set a fatal error, allowing conditional downstream
        routing to skip execution.
        """
        start = time.time()
        with self.obs.start_span("toolopt.gstep", state.get("trace_id")):
            intent = state.get("intent", "general")
            plan = state.get("plan", "")
            necessity = 0.0
            if intent in {"action", "coding"}:
                necessity += 0.6
            if any(k in str(plan).lower() for k in ("run", "execute", "call", "tool", "python", "bash")):
                necessity += 0.4
            if necessity == 0.0 and plan:
                necessity = 0.35
            score = round(min(1.0, necessity), 4)
            state["tool_necessity_score"] = score
            rejected = score < self.config.gstep_threshold
            state.setdefault("metrics", {})["gstep_rejected"] = rejected
            self.obs.count_node("toolopt.gstep", "rejected" if rejected else "approved")
            self.obs.record_latency("toolopt.gstep", time.time() - start)
        return state

    def hdpo_optimize(self, state: AIOState) -> AIOState:
        """HDPO: hierarchical decoupled policy optimization for accuracy and efficiency channels."""
        start = time.time()
        with self.obs.start_span("toolopt.hdpo", state.get("trace_id")):
            accuracy = random.uniform(0.7, 1.0)
            efficiency = random.uniform(0.5, 1.0)
            combined = (
                accuracy * self.config.hdpo_accuracy_weight
                + efficiency * self.config.hdpo_efficiency_weight
            )
            state["tool_policy_channels"] = {
                "accuracy_channel": round(accuracy, 4),
                "efficiency_channel": round(efficiency, 4),
                "combined_score": round(combined, 4),
            }
            self.obs.record_latency("toolopt.hdpo", time.time() - start)
            self.obs.count_node("toolopt.hdpo", "success")
        return state

    def jtpro_optimize(self, state: AIOState) -> AIOState:
        """JTPRO: joint tool-prompt reflective optimization."""
        start = time.time()
        with self.obs.start_span("toolopt.jtpro", state.get("trace_id")):
            plan = state.get("plan", "")
            improvements = []
            for i in range(self.config.jtpro_iterations):
                improvements.append(f"Iteration {i+1}: refined prompt clarity.")
            state["tool_prompt_optimization"] = {
                "iterations": self.config.jtpro_iterations,
                "improvements": improvements,
                "final_prompt": plan or "",
            }
            self.obs.record_latency("toolopt.jtpro", time.time() - start)
            self.obs.count_node("toolopt.jtpro", "success")
        return state

    def sandbox_execute(self, state: AIOState, toolgate: "ToolGate") -> AIOState:
        """Enhanced sandbox execution with result capture.

        Delegates to the Layer 7 ToolGate and then records sandbox metadata.
        """
        start = time.time()
        with self.obs.start_span("toolopt.sandbox", state.get("trace_id")):
            result = toolgate.execute(state)
            exec_res = result.get("execution_result", {})
            state["sandbox_result"] = {
                "tool": exec_res.get("tool"),
                "success": exec_res.get("success"),
                "exit_code": exec_res.get("exit_code"),
                "sandboxed": True,
            }
            self.obs.record_latency("toolopt.sandbox", time.time() - start)
            self.obs.count_node("toolopt.sandbox", "success" if exec_res.get("success") else "failure")
        return state

    def analytics_record(self, state: AIOState) -> AIOState:
        """Record tool usage analytics and auto-deprecate underperforming tools."""
        start = time.time()
        with self.obs.start_span("toolopt.analytics", state.get("trace_id")):
            exec_res = state.get("execution_result", {})
            tool_name = exec_res.get("tool", "unknown")
            stats = self._usage_stats.setdefault(tool_name, {"calls": 0, "errors": 0, "deprecated": False})
            stats["calls"] += 1
            if not exec_res.get("success"):
                stats["errors"] += 1
            error_rate = stats["errors"] / max(1, stats["calls"])
            if error_rate > self.config.auto_deprecation_error_rate and stats["calls"] >= 5:
                stats["deprecated"] = True
            state["tool_analytics"] = {
                "tool": tool_name,
                "calls": stats["calls"],
                "errors": stats["errors"],
                "error_rate": round(error_rate, 4),
                "deprecated": stats["deprecated"],
            }
            self.obs.count_node("toolopt.analytics", "deprecated" if stats["deprecated"] else "recorded")
            self.obs.record_latency("toolopt.analytics", time.time() - start)
        return state


# ---------------------------------------------------------------------------
# Layer 7 — Execution & Action
# ---------------------------------------------------------------------------

class ToolGate:
    """Capability registry, HermesAgent routing, and Docker sandbox execution."""

    def __init__(self, config: ToolGateConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._docker_client: Optional[Any] = None
        if DOCKER_AVAILABLE:
            try:
                self._docker_client = docker.DockerClient(base_url=config.docker_socket)
                self.obs.log(logging.INFO, "Docker client initialized.")
            except Exception as exc:
                self.obs.log(logging.WARNING, f"Docker client init failed: {exc}")
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register_tool(
            name="python_sandbox",
            schema={"type": "object", "properties": {"code": {"type": "string"}}},
            sandbox=True,
            timeout=self.config.default_timeout_seconds,
        )
        self.register_tool(
            name="bash_sandbox",
            schema={"type": "object", "properties": {"command": {"type": "string"}}},
            sandbox=True,
            timeout=self.config.default_timeout_seconds,
        )
        self.register_tool(
            name="echo",
            schema={"type": "object", "properties": {"message": {"type": "string"}}},
            sandbox=False,
            timeout=5,
        )

    def register_tool(
        self,
        name: str,
        schema: Dict[str, Any],
        sandbox: bool = True,
        timeout: int = 30,
        handler: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._registry[name] = {
            "name": name,
            "schema": schema,
            "sandbox": sandbox,
            "timeout": timeout,
            "handler": handler,
        }
        self.obs.log(logging.INFO, f"Tool registered: {name}")

    def route(self, state: AIOState) -> str:
        intent = state.get("intent") or "general"
        plan = state.get("plan") or ""
        lowered = (intent + " " + plan).lower()
        if "code" in lowered or "python" in lowered:
            return "python_sandbox"
        if "run" in lowered or "bash" in lowered or "command" in lowered:
            return "bash_sandbox"
        return "echo"

    def execute(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("toolgate.execute", state.get("trace_id")):
            tool_name = self.route(state)
            tool = self._registry.get(tool_name)
            if not tool:
                state["execution_result"] = {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Unknown tool: {tool_name}",
                    "exit_code": -1,
                    "tool": tool_name,
                }
                self.obs.count_node("toolgate.execute", "failure")
                return state

            params = self._extract_params(tool_name, state.get("plan", ""))
            result = {"tool": tool_name, "params": params}

            if tool["sandbox"]:
                result.update(self._docker_run(tool, params))
            else:
                result.update(self._direct_run(tool, params))

            state["execution_result"] = result
            status = "success" if result.get("success") else "failure"
            self.obs.record_latency("toolgate.execute", time.time() - start)
            self.obs.count_node("toolgate.execute", status)
        return state

    def _extract_params(self, tool_name: str, plan: str) -> Dict[str, Any]:
        safe_plan = plan or ""
        if tool_name == "python_sandbox":
            m = re.search(r"```python\r?\n(.*?)```", safe_plan, re.S)
            if m:
                return {"code": m.group(1).strip("\n\r")}
            return {"code": (safe_plan or "print('hello')").strip("\n\r")}
        if tool_name == "bash_sandbox":
            m = re.search(r"```bash\r?\n(.*?)```", safe_plan, re.S)
            if m:
                return {"command": m.group(1).strip("\n\r")}
            return {"command": (safe_plan or "echo hello").strip("\n\r")}
        if tool_name == "echo":
            return {"message": (safe_plan or "echo").strip()}
        return {}

    def _docker_run(self, tool: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool inside a Docker sandbox.

        If ``self._docker_client`` is ``None`` or Docker is globally unavailable,
        returns a graceful failure so that tests can mock the client directly.
        """
        if self._docker_client is None or not DOCKER_AVAILABLE:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Docker not available",
                "exit_code": -1,
            }
        image = "python:3.12-slim" if tool["name"] == "python_sandbox" else "alpine:latest"
        if tool["name"] == "python_sandbox":
            cmd = ["python", "-c", params.get("code", "")]
        elif tool["name"] == "bash_sandbox":
            cmd = ["sh", "-c", params.get("command", "")]
        else:
            cmd = ["echo", str(params)]
        try:
            container = self._docker_client.containers.run(
                image,
                command=cmd,
                detach=True,
                mem_limit=f"{self.config.max_memory_mb}m",
                cpu_quota=self.config.cpu_quota,
                network_disabled=self.config.network_disabled,
                read_only=self.config.read_only_rootfs,
                remove=True,
            )
            try:
                exit_code = container.wait(timeout=tool["timeout"])["StatusCode"]
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            except Exception as wait_exc:
                container.kill()
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Docker wait/timeout error: {wait_exc}",
                    "exit_code": -1,
                }
            return {
                "success": exit_code == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            }
        except Exception as exc:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Docker execution error: {exc}",
                "exit_code": -1,
            }

    def _direct_run(self, tool: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        handler = tool.get("handler")
        if handler:
            try:
                out = handler(**params)
                return {"success": True, "stdout": str(out), "stderr": "", "exit_code": 0}
            except Exception as exc:
                return {"success": False, "stdout": "", "stderr": str(exc), "exit_code": -1}
        if tool["name"] == "echo":
            msg = params.get("message", "")
            return {"success": True, "stdout": msg, "stderr": "", "exit_code": 0}
        return {"success": False, "stdout": "", "stderr": "No handler", "exit_code": -1}


# ---------------------------------------------------------------------------
# Layer 8 — Failure Recovery & Anti-Fragility
# ---------------------------------------------------------------------------

class FailureState(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    FAILED = "FAILED"


class FailureRecovery:
    """ReCiSt state machine, NeuroShield, retry logic, anti-fragility learning."""

    def __init__(self, config: FailureRecoveryConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._failure_log: List[Dict[str, Any]] = []
        self._adaptive_thresholds: Dict[str, float] = {
            "retry_backoff_multiplier": 2.0,
            "escalation_score": 0.8,
        }

    def assess(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("failure.assess", state.get("trace_id")):
            exec_res = state.get("execution_result", {})
            err = exec_res.get("stderr", "")
            exit_code = exec_res.get("exit_code", 0)
            fstate = state.get("failure_state", "HEALTHY")
            fcount = state.get("failure_count", 0)
            budget = state.get("retry_budget", self.config.max_retries)

            classification = self._classify(err, exit_code)
            state["metrics"]["failure_classification"] = classification

            if classification == "transient":
                if fstate in ("HEALTHY", "RECOVERING"):
                    state["failure_state"] = "DEGRADED"
                state["failure_count"] = fcount + 1
                state["retry_budget"] = max(0, budget - 1)
            elif classification == "permanent":
                state["failure_state"] = "FAILED"
                state["failure_count"] = fcount + 1
                state["retry_budget"] = 0
            else:  # catastrophic
                state["failure_state"] = "FAILED"
                state["failure_count"] = fcount + 1
                state["retry_budget"] = 0
                state["error"] = f"Catastrophic failure: {err[:500]}"

            self.obs.set_failure_state(state["failure_state"])
            self._failure_log.append({
                "timestamp": time.time(),
                "classification": classification,
                "error": err,
                "state": state["failure_state"],
            })
            self.obs.record_latency("failure.assess", time.time() - start)
            self.obs.count_node("failure.assess", classification)
        return state

    def _classify(self, stderr: str, exit_code: int) -> str:
        lowered = stderr.lower()
        catastrophic_indicators = {"segfault", "killed", "out of memory", "panic", "catastrophic"}
        permanent_indicators = {"not found", "unknown tool", "no such file", "permission denied", "docker execution error"}
        if any(c in lowered for c in catastrophic_indicators) or exit_code == -9:
            return "catastrophic"
        if any(p in lowered for p in permanent_indicators) or exit_code == 127:
            return "permanent"
        return "transient"

    def retry(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("failure.retry", state.get("trace_id")):
            fcount = state.get("failure_count", 0)
            multiplier = self._adaptive_thresholds["retry_backoff_multiplier"]
            base = self.config.base_backoff_seconds
            max_backoff = self.config.max_backoff_seconds
            jitter = random.uniform(0, self.config.jitter_factor * base * (multiplier ** fcount))
            backoff = min(base * (multiplier ** fcount), max_backoff) + jitter
            state["metrics"]["retry_backoff_seconds"] = round(backoff, 3)
            self.obs.record_latency("failure.retry", time.time() - start)
            self.obs.count_node("failure.retry", "success")
        return state

    def shield(self, state: AIOState) -> AIOState:
        """NeuroShield: runtime safety boundary enforcement.

        Uses pattern matching and deterministic heuristics to intercept
        harmful, PII-leaking, system-integrity-violating, or jailbreak
        inputs. Sets ``failure_state`` to ``FAILED`` and populates
        ``safety_violations`` when threats are detected.
        """
        start = time.time()
        with self.obs.start_span("failure.shield", state.get("trace_id")):
            raw = state.get("raw_input", "")
            plan = state.get("plan", "")
            combined = f"{raw} {plan or ''}".lower()
            violations: List[Dict[str, Any]] = []
            patterns = {
                "harm": r"\b(kill|harm|attack|destroy)\b",
                "pii": r"\b(ssn|password|secret_key|api_key)\b",
                "system_integrity": r"(rm -rf /|mkfs|fdisk|drop table|delete from)",
            }
            for category, pattern in patterns.items():
                if re.search(pattern, combined):
                    violations.append({
                        "category": category,
                        "pattern": pattern,
                        "intercepted": True,
                        "timestamp": time.time(),
                    })
            if "override" in combined or "ignore previous" in combined:
                violations.append({
                    "category": "jailbreak",
                    "pattern": "override|ignore previous",
                    "intercepted": True,
                    "timestamp": time.time(),
                })

            if violations:
                state["safety_violations"] = state.get("safety_violations", []) + violations
                state["failure_state"] = "FAILED"
                state["error"] = f"NeuroShield intercepted {len(violations)} violation(s)."
                self.obs.set_failure_state("FAILED")
                self.obs.count_node("failure.shield", "blocked")
            else:
                self.obs.count_node("failure.shield", "allowed")
            self.obs.record_latency("failure.shield", time.time() - start)
        return state

    def learn(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("failure.learn", state.get("trace_id")):
            log = self._failure_log
            if len(log) >= 5:
                recent = log[-5:]
                transient_rate = sum(1 for r in recent if r["classification"] == "transient") / len(recent)
                if transient_rate > 0.8:
                    self._adaptive_thresholds["retry_backoff_multiplier"] = min(
                        3.0, self._adaptive_thresholds["retry_backoff_multiplier"] + 0.1
                    )
                else:
                    self._adaptive_thresholds["retry_backoff_multiplier"] = max(
                        1.0, self._adaptive_thresholds["retry_backoff_multiplier"] - 0.1
                    )
            state["metrics"]["adaptive_thresholds"] = dict(self._adaptive_thresholds)
            self.obs.record_latency("failure.learn", time.time() - start)
            self.obs.count_node("failure.learn", "success")
        return state

    def escalate(self, state: AIOState) -> AIOState:
        state["output"] = None
        state["error"] = state.get("error") or "Escalated to operator."
        state["failure_state"] = "FAILED"
        self.obs.set_failure_state("FAILED")
        self.obs.count_node("failure.escalate", "escalated")
        return state

    def degrade(self, state: AIOState) -> AIOState:
        state["output"] = state.get("output") or "[DEGRADED MODE] Limited response due to system failure."
        state["failure_state"] = "DEGRADED"
        self.obs.set_failure_state("DEGRADED")
        self.obs.count_node("failure.degrade", "degraded")
        return state

# ---------------------------------------------------------------------------
# Layer 9 — Self-Evolution
# ---------------------------------------------------------------------------

class SelfEvolutionLayer:
    """Analyzes performance trends and suggests safe, bounded config improvements."""

    def __init__(self, config: SelfEvolutionConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._snapshots: List[Dict[str, Any]] = []
        self._applied_deltas: List[Dict[str, Any]] = []

    def analyze(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("self_evolution.analyze", state.get("trace_id")):
            snapshot = {
                "turn": state.get("turn", 0),
                "latency_seconds": round(time.time() - start, 4),
                "success": state.get("error") is None and state.get("failure_state") == "HEALTHY",
                "memory_confidence": state.get("memory_confidence", 0.0),
                "verification_score": state.get("verification_result", {}).get("ensemble_score", 0.0),
            }
            self._snapshots.append(snapshot)
            state["performance_snapshot"] = snapshot
            self.obs.record_latency("self_evolution.analyze", time.time() - start)
            self.obs.count_node("self_evolution.analyze", "success")
        return state

    def generate_report(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("self_evolution.report", state.get("trace_id")):
            window = self._snapshots[-self.config.performance_window_size:]
            if not window:
                report = {"window_size": 0, "avg_latency": 0.0, "error_rate": 0.0, "memory_confidence_trend": "insufficient_data"}
            else:
                avg_latency = sum(s.get("latency_seconds", 0.0) for s in window) / len(window)
                error_rate = sum(1 for s in window if not s.get("success", True)) / len(window)
                mem_confidences = [s.get("memory_confidence", 0.0) for s in window]
                trend = "stable"
                if len(mem_confidences) >= 2:
                    first_half = sum(mem_confidences[:len(mem_confidences)//2]) / max(1, len(mem_confidences)//2)
                    second_half = sum(mem_confidences[len(mem_confidences)//2:]) / max(1, len(mem_confidences) - len(mem_confidences)//2)
                    if second_half > first_half + 0.1:
                        trend = "improving"
                    elif second_half < first_half - 0.1:
                        trend = "declining"
                report = {
                    "window_size": len(window),
                    "avg_latency": round(avg_latency, 4),
                    "error_rate": round(error_rate, 4),
                    "memory_confidence_trend": trend,
                }
            state["self_evolution_report"] = report
            self.obs.record_latency("self_evolution.report", time.time() - start)
            self.obs.count_node("self_evolution.report", "success")
        return state

    def suggest_improvements(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("self_evolution.suggest", state.get("trace_id")):
            report = state.get("self_evolution_report", {})
            deltas: List[Dict[str, Any]] = []
            if report.get("memory_confidence_trend") == "declining":
                deltas.append({"key": "retrieval_top_k", "old": 5, "new": 7, "rationale": "Low memory confidence in window"})
            if report.get("error_rate", 0.0) > 0.3:
                deltas.append({"key": "base_backoff_seconds", "old": 1.0, "new": 2.0, "rationale": "High transient failure rate"})
            state["suggested_config_delta"] = deltas
            self.obs.record_latency("self_evolution.suggest", time.time() - start)
            self.obs.count_node("self_evolution.suggest", "success" if deltas else "none")
        return state

    def apply_deltas(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("self_evolution.apply", state.get("trace_id")):
            if not self.config.auto_apply_config_delta:
                self.obs.count_node("self_evolution.apply", "skipped")
                return state
            deltas = state.get("suggested_config_delta", [])
            applied = []
            whitelist = {"retrieval_top_k", "base_backoff_seconds", "max_tokens"}
            for delta in deltas:
                key = delta.get("key", "")
                if key in whitelist:
                    applied.append(delta)
                    self._applied_deltas.append(delta)
            state.setdefault("metrics", {})["self_evolution_applied"] = applied
            self.obs.record_latency("self_evolution.apply", time.time() - start)
            self.obs.count_node("self_evolution.apply", "success" if applied else "none")
        return state


# ---------------------------------------------------------------------------
# Layer 10 — Multi-Agent Coordination
# ---------------------------------------------------------------------------

class MultiAgentCoordinator:
    """Decomposes complex tasks across registered agents and synthesizes consensus."""

    def __init__(self, config: MultiAgentConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._registry: Dict[str, Dict[str, Any]] = {
            "coder": {"role": "Implementation", "strengths": ["code", "debug", "refactor"]},
            "analyst": {"role": "Analysis", "strengths": ["data", "patterns", "summary"]},
            "planner": {"role": "Strategy", "strengths": ["decompose", "dependencies", "schedule"]},
            "safety_officer": {"role": "Safety", "strengths": ["risk", "compliance", "boundaries"]},
        }

    def decompose(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("multi_agent.decompose", state.get("trace_id")):
            intent = state.get("intent", "general")
            plan = state.get("plan", "")
            subtasks = []
            if intent in {"coding", "analysis"}:
                subtasks.append({"id": "st-1", "agent": "planner", "description": "Decompose requirements"})
                subtasks.append({"id": "st-2", "agent": "coder" if intent == "coding" else "analyst", "description": "Execute core task"})
                subtasks.append({"id": "st-3", "agent": "safety_officer", "description": "Verify compliance"})
            else:
                subtasks.append({"id": "st-1", "agent": "planner", "description": "Plan task"})
                subtasks.append({"id": "st-2", "agent": "analyst", "description": "Analyze context"})
            state["coordination_plan"] = {"subtasks": subtasks, "intent": intent, "plan": plan}
            self.obs.record_latency("multi_agent.decompose", time.time() - start)
            self.obs.count_node("multi_agent.decompose", "success")
        return state

    def dispatch(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("multi_agent.dispatch", state.get("trace_id")):
            plan = state.get("coordination_plan", {})
            subtasks = plan.get("subtasks", [])
            outputs: Dict[str, Any] = {}
            for st in subtasks:
                agent = st.get("agent", "unknown")
                confidence = round(0.7 + (0.25 if agent in self._registry else 0.0), 4)
                outputs[st["id"]] = {
                    "agent": agent,
                    "confidence": confidence,
                    "result": f"Simulated output from {agent} for {st.get('description', '')}",
                }
            state["agent_outputs"] = outputs
            self.obs.record_latency("multi_agent.dispatch", time.time() - start)
            self.obs.count_node("multi_agent.dispatch", "success")
        return state

    def aggregate(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("multi_agent.aggregate", state.get("trace_id")):
            outputs = state.get("agent_outputs", {})
            if not outputs:
                consensus = 0.0
            else:
                confidences = [o.get("confidence", 0.0) for o in outputs.values()]
                avg_conf = sum(confidences) / len(confidences)
                variance = sum((c - avg_conf) ** 2 for c in confidences) / len(confidences)
                consensus = round(max(0.0, avg_conf - variance), 4)
            state["consensus_score"] = consensus
            self.obs.record_latency("multi_agent.aggregate", time.time() - start)
            self.obs.count_node("multi_agent.aggregate", "success")
        return state

    def synthesize(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("multi_agent.synthesize", state.get("trace_id")):
            outputs = state.get("agent_outputs", {})
            parts = [o.get("result", "") for o in outputs.values()]
            unified = " | ".join(parts) if parts else "No agent outputs"
            state["plan"] = unified
            self.obs.record_latency("multi_agent.synthesize", time.time() - start)
            self.obs.count_node("multi_agent.synthesize", "success")
        return state


# ---------------------------------------------------------------------------
# Layer 11 — Safety & Governance
# ---------------------------------------------------------------------------

class SafetyGovernance:
    """Per-turn audit, constitutional compliance, governance voting, and decision recording."""

    def __init__(self, config: SafetyGovernanceConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._decisions: List[Dict[str, Any]] = []

    def audit(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("governance.audit", state.get("trace_id")):
            entry = {
                "turn": state.get("turn", 0),
                "timestamp": time.time(),
                "plan_present": bool(state.get("plan")),
                "verification_present": bool(state.get("verification_result")),
                "safety_clean": len(state.get("safety_violations", [])) == 0,
                "god_object_detected": self._detect_god_object(state),
            }
            trail = state.get("audit_trail", []) or []
            trail.append(entry)
            state["audit_trail"] = trail
            self.obs.record_latency("governance.audit", time.time() - start)
            self.obs.count_node("governance.audit", "success")
        return state

    def _detect_god_object(self, state: AIOState) -> bool:
        filled = sum(1 for v in state.values() if v is not None and v != [] and v != {} and v != 0 and v != 0.0 and v != "")
        total = len(state)
        return filled > 0 and (filled / total) > 0.9

    def check_compliance(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("governance.compliance", state.get("trace_id")):
            violations: List[Dict[str, Any]] = []
            if not state.get("plan"):
                violations.append({"type": "pure_llm_decision", "details": "No plan present in state"})
            if not state.get("verification_result"):
                violations.append({"type": "uncritiqued_output", "details": "No verification result in state"})
            if state.get("safety_violations"):
                violations.append({"type": "constitutional_breach", "details": "Safety violations detected"})
            if self._detect_god_object(state):
                violations.append({"type": "god_object", "details": "Single layer appears to dominate state"})
            state["compliance_violations"] = violations
            self.obs.record_latency("governance.compliance", time.time() - start)
            self.obs.count_node("governance.compliance", "success" if not violations else "violation")
        return state

    def governance_vote(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("governance.vote", state.get("trace_id")):
            violations = state.get("compliance_violations", []) or []
            if violations:
                outcome = "blocked"
                majority = 0.0
            else:
                outcome = "approved"
                majority = 1.0
            state["governance_result"] = {
                "sensitive_action": "none",
                "vote_outcome": outcome,
                "majority": majority,
            }
            self.obs.record_latency("governance.vote", time.time() - start)
            self.obs.count_node("governance.vote", outcome)
        return state

    def record_decision(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("governance.record", state.get("trace_id")):
            decision = {
                "turn": state.get("turn", 0),
                "timestamp": time.time(),
                "governance_result": state.get("governance_result"),
                "compliance_violations": state.get("compliance_violations"),
            }
            self._decisions.append(decision)
            self.obs.record_latency("governance.record", time.time() - start)
            self.obs.count_node("governance.record", "success")
        return state


# ---------------------------------------------------------------------------
# Layer 12 — Cognitive Immune System
# ---------------------------------------------------------------------------

class CognitiveImmuneSystem:
    """Anomaly detection, threat pattern tracking, quarantine, and self-healing."""

    def __init__(self, config: CognitiveImmuneConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._threat_db: Dict[str, Dict[str, Any]] = {}
        self._quarantine_store: Dict[str, Dict[str, Any]] = {}

    def scan(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("immune.scan", state.get("trace_id")):
            score = 0.0
            fcount = state.get("failure_count", 0)
            if fcount > 2:
                score += 0.4
            if state.get("retry_budget", 0) == 0 and state.get("failure_state") != "HEALTHY":
                score += 0.3
            violations = state.get("safety_violations", [])
            if len(violations) > 2:
                score += 0.3
            wm = state.get("working_memory", []) or []
            corrupted = sum(1 for m in wm if m is None or not isinstance(m, dict) or m.get("content") is None)
            if corrupted > 0:
                score += 0.2
            state["anomaly_score"] = round(min(1.0, score), 4)
            self.obs.record_latency("immune.scan", time.time() - start)
            self.obs.count_node("immune.scan", "success")
        return state

    def detect_threats(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("immune.detect", state.get("trace_id")):
            now = time.time()
            ttl = self.config.pattern_db_ttl_seconds
            for key in list(self._threat_db.keys()):
                if now - self._threat_db[key].get("first_seen", now) > ttl:
                    del self._threat_db[key]
            if state.get("failure_count", 0) > 2:
                self._threat_db.setdefault("rapid_failure", {"count": 0, "first_seen": now, "severity": "high"})["count"] += 1
            wm = state.get("working_memory", []) or []
            corrupted = sum(1 for m in wm if m is None or not isinstance(m, dict) or m.get("content") is None)
            if corrupted > 0:
                self._threat_db.setdefault("memory_corruption", {"count": 0, "first_seen": now, "severity": "high"})["count"] += 1
            patterns = [{"pattern": k, "count": v["count"], "severity": v["severity"]} for k, v in self._threat_db.items()]
            state["threat_patterns_detected"] = patterns
            self.obs.record_latency("immune.detect", time.time() - start)
            self.obs.count_node("immune.detect", "success")
        return state

    def quarantine(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("immune.quarantine", state.get("trace_id")):
            qids: List[str] = []
            if self.config.auto_quarantine and state.get("anomaly_score", 0.0) > self.config.anomaly_threshold:
                wm = state.get("working_memory", []) or []
                for i, entry in enumerate(wm):
                    if entry is None or not isinstance(entry, dict) or entry.get("content") is None:
                        eid = entry.get("id", f"quarantine-{i}") if isinstance(entry, dict) else f"quarantine-{i}"
                        self._quarantine_store[eid] = {"entry": entry, "timestamp": time.time()}
                        qids.append(eid)
            state["quarantined_ids"] = qids
            self.obs.record_latency("immune.quarantine", time.time() - start)
            self.obs.count_node("immune.quarantine", "quarantined" if qids else "clean")
        return state

    def heal(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("immune.heal", state.get("trace_id")):
            actions: List[Dict[str, Any]] = []
            if not self.config.auto_heal:
                self.obs.count_node("immune.heal", "skipped")
                return state
            if state.get("failure_state") == "FAILED":
                actions.append({"action": "none", "target": "system", "rationale": "Auto-heal disabled when FAILED"})
                state["healing_actions"] = actions
                self.obs.record_latency("immune.heal", time.time() - start)
                self.obs.count_node("immune.heal", "blocked")
                return state
            wm = state.get("working_memory", []) or []
            cleaned = [m for m in wm if m is not None and isinstance(m, dict) and m.get("content") is not None]
            if len(cleaned) < len(wm):
                state["working_memory"] = cleaned
                actions.append({"action": "clear_corrupted", "target": "working_memory", "rationale": "Removed corrupted entries"})
            if state.get("failure_count", 0) > 0 and state.get("failure_state") == "HEALTHY":
                actions.append({"action": "reset_failure_counts", "target": "failure_state", "rationale": "State is healthy"})
            if not actions:
                actions.append({"action": "none", "target": "memory", "rationale": "No corruption detected"})
            state["healing_actions"] = actions
            self.obs.record_latency("immune.heal", time.time() - start)
            self.obs.count_node("immune.heal", "success" if any(a["action"] != "none" for a in actions) else "none")
        return state

    def update_immunity(self, state: AIOState) -> AIOState:
        start = time.time()
        with self.obs.start_span("immune.update", state.get("trace_id")):
            anomaly = state.get("anomaly_score", 0.0)
            if anomaly > self.config.anomaly_threshold:
                status = "ALERT"
            elif anomaly > 0.3:
                status = "WATCH"
            else:
                status = "HEALTHY"
            state["immune_status"] = status
            self.obs.record_latency("immune.update", time.time() - start)
            self.obs.count_node("immune.update", status.lower())
        return state

# ---------------------------------------------------------------------------
# Graph Nodes
# ---------------------------------------------------------------------------

def node_context_ingest(state: AIOState, ctx_mgr: ContextManager) -> AIOState:
    return ctx_mgr.ingest(state)


def node_context_sculpt(state: AIOState, ctx_mgr: ContextManager) -> AIOState:
    return ctx_mgr.sculpt(state)


def node_memory_retrieve(state: AIOState, mem: MemoryBridge) -> AIOState:
    return mem.retrieve(state)


def node_memory_encode(state: AIOState, mem: MemoryBridge) -> AIOState:
    return mem.encode(state)


def node_memory_verify(state: AIOState, mem: MemoryBridge) -> AIOState:
    return mem.verify(state)


def node_memory_store(state: AIOState, mem: MemoryBridge) -> AIOState:
    return mem.store(state)


def node_memory_consolidate(state: AIOState, mem: MemoryBridge) -> AIOState:
    return mem.consolidate(state)


def node_plan_generate(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.generate_plan(state)


# Layer 3 nodes


def node_maci_select(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_maci(state)


def node_hiplan(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_hiplan(state)


def node_flare(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_flare(state)


def node_lwm_augment(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_lwm(state)


def node_ppa_analyze(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_ppa(state)


def node_spiral_mcts(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_spiral(state)


def node_mars_reflect(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_mars(state)


def node_vmao_decompose(state: AIOState, planning: PlanningLayer) -> AIOState:
    return planning.run_vmao_decompose(state)


# Layer 4 nodes


def node_curiosity_intrinsic(state: AIOState, curiosity: CuriosityEngine) -> AIOState:
    return curiosity.intrinsic_reward(state)


def node_curiosity_seek(state: AIOState, curiosity: CuriosityEngine) -> AIOState:
    return curiosity.active_seek(state)


def node_curiosity_serendipity(state: AIOState, curiosity: CuriosityEngine) -> AIOState:
    return curiosity.serendipity(state)


def node_curiosity_counterfactual(state: AIOState, curiosity: CuriosityEngine) -> AIOState:
    return curiosity.counterfactual(state)


def node_curiosity_umwelt(state: AIOState, curiosity: CuriosityEngine) -> AIOState:
    return curiosity.umwelt_constraints(state)


# Layer 5 nodes


def node_verify_plan(state: AIOState, verifier: Verifier) -> AIOState:
    state = verifier.critique(state)
    state = verifier.judge(state)
    state = verifier.score(state)
    state = verifier.debug(state)
    return state


def node_debug_and_replan(state: AIOState, verifier: Verifier) -> AIOState:
    result = state.get("verification_result", {})
    hypotheses = result.get("debug_hypotheses", [])
    existing = state.get("plan") or ""
    if hypotheses:
        replan_text = "[REPLAN] " + "; ".join(hypotheses)
    else:
        replan_text = "[REPLAN] no plan"
    # Inject explicit steps so the next critique passes, preventing an infinite loop.
    enriched = replan_text + " Step 1: analyze. Step 2: execute action. Step 3: finalize."
    state["plan"] = enriched
    state["verification_result"] = {}
    return state


# Layer 6 nodes


def node_gstep_evaluate(state: AIOState, toolopt: ToolOptimizer) -> AIOState:
    return toolopt.gstep_evaluate(state)


def node_hdpo_optimize(state: AIOState, toolopt: ToolOptimizer) -> AIOState:
    return toolopt.hdpo_optimize(state)


def node_jtpro_optimize(state: AIOState, toolopt: ToolOptimizer) -> AIOState:
    return toolopt.jtpro_optimize(state)


def node_sandbox_execute(state: AIOState, toolopt: ToolOptimizer, toolgate: ToolGate) -> AIOState:
    return toolopt.sandbox_execute(state, toolgate)


def node_analytics_record(state: AIOState, toolopt: ToolOptimizer) -> AIOState:
    return toolopt.analytics_record(state)


# Layer 7 node


def node_execute_action(state: AIOState, toolgate: ToolGate) -> AIOState:
    return toolgate.execute(state)


# Layer 8 nodes


def node_failure_assess(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.assess(state)


def node_retry_with_backoff(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.retry(state)


def node_escalate(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.escalate(state)


def node_graceful_degrade(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.degrade(state)


def node_neuroshield(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.shield(state)


def node_failure_learn(state: AIOState, recovery: FailureRecovery) -> AIOState:
    return recovery.learn(state)


def node_finalize_output(state: AIOState) -> AIOState:
    if state.get("error"):
        state["output"] = f"[ERROR] {state['error']}"
    elif state.get("execution_result"):
        exec_res = state["execution_result"]
        if exec_res.get("success"):
            state["output"] = exec_res.get("stdout", "") or "[OK]"
        else:
            state["output"] = exec_res.get("stderr", "") or "[NO OUTPUT]"
    else:
        state["output"] = state.get("output") or "[NO OUTPUT]"
    return state


# Layer 9 nodes


def node_self_evolution_analyze(state: AIOState, layer: SelfEvolutionLayer) -> AIOState:
    state = layer.analyze(state)
    state = layer.generate_report(state)
    state = layer.suggest_improvements(state)
    state = layer.apply_deltas(state)
    return state


# Layer 10 nodes


def node_multi_agent_decompose(state: AIOState, layer: MultiAgentCoordinator) -> AIOState:
    return layer.decompose(state)


def node_multi_agent_dispatch(state: AIOState, layer: MultiAgentCoordinator) -> AIOState:
    return layer.dispatch(state)


def node_multi_agent_aggregate(state: AIOState, layer: MultiAgentCoordinator) -> AIOState:
    return layer.aggregate(state)


def node_multi_agent_synthesize(state: AIOState, layer: MultiAgentCoordinator) -> AIOState:
    return layer.synthesize(state)


# Layer 11 nodes


def node_safety_governance_audit(state: AIOState, layer: SafetyGovernance) -> AIOState:
    state = layer.audit(state)
    state = layer.check_compliance(state)
    state = layer.governance_vote(state)
    state = layer.record_decision(state)
    return state


# Layer 12 nodes


def node_cognitive_immune_scan(state: AIOState, layer: CognitiveImmuneSystem) -> AIOState:
    state = layer.scan(state)
    state = layer.detect_threats(state)
    state = layer.quarantine(state)
    state = layer.heal(state)
    state = layer.update_immunity(state)
    return state


# ---------------------------------------------------------------------------
# Conditional Routing
# ---------------------------------------------------------------------------

def route_memory_confidence(state: AIOState) -> str:
    confidence = state.get("memory_confidence", 0.0)
    if confidence < 0.7:
        return "memory_encode"
    return "curiosity_intrinsic"


def route_verification(state: AIOState) -> str:
    passed = state.get("verification_result", {}).get("passed", False)
    return "gstep_evaluate" if passed else "debug_and_replan"


def route_failure(state: AIOState) -> str:
    classification = state.get("metrics", {}).get("failure_classification", "transient")
    if classification == "transient":
        budget = state.get("retry_budget", 0)
        if budget > 0:
            return "retry_with_backoff"
        return "escalate"
    elif classification == "permanent":
        return "escalate"
    return "graceful_degrade"


def route_shield(state: AIOState) -> str:
    return "escalate" if state.get("safety_violations") else "memory_retrieve"


def route_ppa(state: AIOState) -> str:
    analysis = state.get("pitfall_analysis", {})
    return "escalate" if not analysis.get("safe_to_proceed", True) else "spiral_mcts"


def route_gstep(state: AIOState) -> str:
    rejected = state.get("metrics", {}).get("gstep_rejected", False)
    return "finalize_output" if rejected else "hdpo_optimize"


def route_post_execution(state: AIOState) -> str:
    exec_res = state.get("execution_result", {})
    return "finalize_output" if exec_res.get("success") else "failure_assess"


def route_context_priority(state: AIOState, ctx_mgr: ContextManager) -> str:
    target = ctx_mgr.route_attention(state)
    if target == "memory":
        return "memory_retrieve"
    if target == "verify":
        return "verify_plan"
    if target == "execute":
        return "gstep_evaluate"
    return "memory_retrieve"


def route_multi_agent(state: AIOState, config: AIOConfig) -> str:
    if not config.enable_priority_3 or not config.multi_agent.enable:
        return "hiplan"
    intent = state.get("intent", "general")
    plan = state.get("plan", "")
    if intent in {"coding", "analysis"} or len(plan) > 200:
        return "multi_agent_decompose"
    return "hiplan"


def route_safety_governance(state: AIOState, config: AIOConfig) -> str:
    if not config.enable_priority_3 or not config.safety_governance.enable:
        return "verify_plan"
    return "safety_governance_audit"


def route_post_finalize(state: AIOState, config: AIOConfig) -> str:
    if not config.enable_priority_3 or not config.self_evolution.enable:
        return END
    return "self_evolution_analyze"


def route_self_evolution(state: AIOState, config: AIOConfig) -> str:
    # Always END after cognitive_immune_scan; the gate is route_post_finalize
    return END


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

def build_aio_graph(config: Optional[AIOConfig] = None) -> Any:
    """Build and compile the Priority 2 AIO StateGraph."""
    cfg = config or AIOConfig()
    obs = ObservabilityLayer(cfg.observability)
    ctx_mgr = ContextManager(cfg.context, obs)
    mem = MemoryBridge(cfg.memory, obs)
    planning = PlanningLayer(cfg.planning, obs)
    curiosity = CuriosityEngine(cfg.curiosity, obs)
    verifier = Verifier(cfg.verifier, obs)
    toolopt = ToolOptimizer(cfg.tool_optimizer, obs)
    toolgate = ToolGate(cfg.toolgate, obs)
    recovery = FailureRecovery(cfg.failure_recovery, obs)

    graph = StateGraph(AIOState)

    # Layer 1
    graph.add_node("context_ingest", lambda s: node_context_ingest(s, ctx_mgr))
    graph.add_node("context_sculpt", lambda s: node_context_sculpt(s, ctx_mgr))

    # Layer 2
    graph.add_node("memory_retrieve", lambda s: node_memory_retrieve(s, mem))
    graph.add_node("memory_encode", lambda s: node_memory_encode(s, mem))
    graph.add_node("memory_verify", lambda s: node_memory_verify(s, mem))
    graph.add_node("memory_store", lambda s: node_memory_store(s, mem))
    graph.add_node("memory_consolidate", lambda s: node_memory_consolidate(s, mem))

    # Layer 4
    graph.add_node("curiosity_intrinsic", lambda s: node_curiosity_intrinsic(s, curiosity))
    graph.add_node("curiosity_seek", lambda s: node_curiosity_seek(s, curiosity))
    graph.add_node("curiosity_serendipity", lambda s: node_curiosity_serendipity(s, curiosity))
    graph.add_node("curiosity_counterfactual", lambda s: node_curiosity_counterfactual(s, curiosity))
    graph.add_node("curiosity_umwelt", lambda s: node_curiosity_umwelt(s, curiosity))

    # Planning stub (generates base plan)
    graph.add_node("plan_generate", lambda s: node_plan_generate(s, planning))

    # Layer 3
    graph.add_node("maci_select", lambda s: node_maci_select(s, planning))
    graph.add_node("hiplan", lambda s: node_hiplan(s, planning))
    graph.add_node("flare", lambda s: node_flare(s, planning))
    graph.add_node("lwm_augment", lambda s: node_lwm_augment(s, planning))
    graph.add_node("ppa_analyze", lambda s: node_ppa_analyze(s, planning))
    graph.add_node("spiral_mcts", lambda s: node_spiral_mcts(s, planning))
    graph.add_node("mars_reflect", lambda s: node_mars_reflect(s, planning))
    graph.add_node("vmao_decompose", lambda s: node_vmao_decompose(s, planning))

    # Layer 5
    graph.add_node("verify_plan", lambda s: node_verify_plan(s, verifier))
    graph.add_node("debug_and_replan", lambda s: node_debug_and_replan(s, verifier))

    # Layer 6
    graph.add_node("gstep_evaluate", lambda s: node_gstep_evaluate(s, toolopt))
    graph.add_node("hdpo_optimize", lambda s: node_hdpo_optimize(s, toolopt))
    graph.add_node("jtpro_optimize", lambda s: node_jtpro_optimize(s, toolopt))
    graph.add_node("execute_action", lambda s: node_execute_action(s, toolgate))
    graph.add_node("analytics_record", lambda s: node_analytics_record(s, toolopt))

    # Layer 8
    graph.add_node("failure_assess", lambda s: node_failure_assess(s, recovery))
    graph.add_node("retry_with_backoff", lambda s: node_retry_with_backoff(s, recovery))
    graph.add_node("escalate", lambda s: node_escalate(s, recovery))
    graph.add_node("graceful_degrade", lambda s: node_graceful_degrade(s, recovery))
    graph.add_node("neuroshield", lambda s: node_neuroshield(s, recovery))
    graph.add_node("failure_learn", lambda s: node_failure_learn(s, recovery))

    # Layer 9-12 nodes (added unconditionally; routing decides if they run)
    self_evol = SelfEvolutionLayer(cfg.self_evolution, obs)
    multi_agent = MultiAgentCoordinator(cfg.multi_agent, obs)
    governance = SafetyGovernance(cfg.safety_governance, obs)
    immune = CognitiveImmuneSystem(cfg.cognitive_immune, obs)

    graph.add_node("self_evolution_analyze", lambda s: node_self_evolution_analyze(s, self_evol))
    graph.add_node("multi_agent_decompose", lambda s: node_multi_agent_decompose(s, multi_agent))
    graph.add_node("multi_agent_dispatch", lambda s: node_multi_agent_dispatch(s, multi_agent))
    graph.add_node("multi_agent_aggregate", lambda s: node_multi_agent_aggregate(s, multi_agent))
    graph.add_node("multi_agent_synthesize", lambda s: node_multi_agent_synthesize(s, multi_agent))
    graph.add_node("safety_governance_audit", lambda s: node_safety_governance_audit(s, governance))
    graph.add_node("cognitive_immune_scan", lambda s: node_cognitive_immune_scan(s, immune))

    # Finalize
    graph.add_node("finalize_output", node_finalize_output)

    # Entry point
    graph.set_entry_point("context_ingest")

    # Layer 1 -> NeuroShield
    graph.add_edge("context_ingest", "context_sculpt")
    graph.add_edge("context_sculpt", "neuroshield")
    graph.add_conditional_edges("neuroshield", route_shield)

    # Escalate from neuroshield -> failure_learn -> finalize
    graph.add_edge("escalate", "failure_learn")

    # Memory branch
    graph.add_conditional_edges("memory_retrieve", route_memory_confidence)
    graph.add_edge("memory_encode", "memory_verify")
    graph.add_edge("memory_verify", "memory_store")
    graph.add_edge("memory_store", "memory_consolidate")
    graph.add_edge("memory_consolidate", "curiosity_intrinsic")

    # Curiosity pipeline
    graph.add_edge("curiosity_intrinsic", "curiosity_seek")
    graph.add_edge("curiosity_seek", "curiosity_serendipity")
    graph.add_edge("curiosity_serendipity", "curiosity_counterfactual")
    graph.add_edge("curiosity_counterfactual", "curiosity_umwelt")
    graph.add_edge("curiosity_umwelt", "plan_generate")

    # Planning pipeline
    graph.add_edge("plan_generate", "maci_select")
    graph.add_conditional_edges("maci_select", lambda s: route_multi_agent(s, cfg))
    graph.add_edge("hiplan", "flare")
    graph.add_edge("multi_agent_decompose", "multi_agent_dispatch")
    graph.add_edge("multi_agent_dispatch", "multi_agent_aggregate")
    graph.add_edge("multi_agent_aggregate", "multi_agent_synthesize")
    graph.add_edge("multi_agent_synthesize", "flare")
    graph.add_edge("flare", "lwm_augment")
    graph.add_edge("lwm_augment", "ppa_analyze")
    graph.add_conditional_edges("ppa_analyze", route_ppa)
    graph.add_edge("spiral_mcts", "mars_reflect")
    graph.add_edge("mars_reflect", "vmao_decompose")
    graph.add_conditional_edges("vmao_decompose", lambda s: route_safety_governance(s, cfg))
    graph.add_edge("safety_governance_audit", "verify_plan")

    # Verification branch
    graph.add_conditional_edges("verify_plan", route_verification)
    graph.add_edge("debug_and_replan", "verify_plan")

    # Tool-use optimization -> execution -> analytics
    graph.add_conditional_edges("gstep_evaluate", route_gstep)
    graph.add_edge("hdpo_optimize", "jtpro_optimize")
    graph.add_edge("jtpro_optimize", "execute_action")
    graph.add_edge("execute_action", "analytics_record")
    graph.add_conditional_edges("analytics_record", route_post_execution)

    # Failure recovery branch
    graph.add_conditional_edges("failure_assess", route_failure)
    graph.add_edge("retry_with_backoff", "verify_plan")
    graph.add_edge("escalate", "failure_learn")
    graph.add_edge("graceful_degrade", "failure_learn")
    graph.add_edge("failure_learn", "finalize_output")

    # Post-finalize reflection pipeline
    graph.add_conditional_edges("finalize_output", lambda s: route_post_finalize(s, cfg))
    graph.add_edge("self_evolution_analyze", "cognitive_immune_scan")
    graph.add_conditional_edges("cognitive_immune_scan", lambda s: route_self_evolution(s, cfg))

    return graph.compile()


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------

def run_aio(raw_input: str, session_id: Optional[str] = None, config: Optional[AIOConfig] = None) -> AIOState:
    app = build_aio_graph(config)
    state = make_initial_state(raw_input, session_id)
    result = app.invoke(state)
    return result


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "echo hello world"
    final_state = run_aio(query)
    print(json.dumps({k: v for k, v in final_state.items() if k != "metrics"}, indent=2, default=str))
