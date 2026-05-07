from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Optional dependency handling
# ---------------------------------------------------------------------------
try:
    from langgraph.graph import StateGraph, END
except Exception as _e:  # pragma: no cover
    StateGraph = None  # type: ignore[misc,assignment]
    END = None  # type: ignore[misc,assignment]
    raise ImportError("langgraph is required. Install: pip install langgraph>=0.0.50") from _e

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    OTEL_AVAILABLE = True
except Exception:  # pragma: no cover
    trace = None  # type: ignore[misc]
    TracerProvider = None  # type: ignore[misc,assignment]
    BatchSpanProcessor = None  # type: ignore[misc,assignment]
    ConsoleSpanExporter = None  # type: ignore[misc,assignment]
    Resource = None  # type: ignore[misc,assignment]
    SERVICE_NAME = None  # type: ignore[misc,assignment]
    OTLPSpanExporter = None  # type: ignore[misc,assignment]
    OTEL_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except Exception:  # pragma: no cover
    Counter = None  # type: ignore[misc,assignment]
    Histogram = None  # type: ignore[misc,assignment]
    Gauge = None  # type: ignore[misc,assignment]
    start_http_server = None  # type: ignore[misc,assignment]
    PROMETHEUS_AVAILABLE = False

try:
    import docker
    DOCKER_AVAILABLE = True
except Exception:  # pragma: no cover
    docker = None  # type: ignore[misc]
    DOCKER_AVAILABLE = False

try:
    from langsmith import Client as LangSmithClient
    LANGSMITH_AVAILABLE = True
except Exception:  # pragma: no cover
    LangSmithClient = None  # type: ignore[misc,assignment]
    LANGSMITH_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore[misc,assignment]
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_OPENAI_AVAILABLE = True
except Exception:  # pragma: no cover
    ChatOpenAI = None  # type: ignore[misc,assignment]
    LANGCHAIN_OPENAI_AVAILABLE = False

try:
    from langchain_anthropic import ChatAnthropic
    LANGCHAIN_ANTHROPIC_AVAILABLE = True
except Exception:  # pragma: no cover
    ChatAnthropic = None  # type: ignore[misc,assignment]
    LANGCHAIN_ANTHROPIC_AVAILABLE = False

LANGCHAIN_CHAT_AVAILABLE = LANGCHAIN_OPENAI_AVAILABLE or LANGCHAIN_ANTHROPIC_AVAILABLE

try:
    import redis
    REDIS_AVAILABLE = True
except Exception:  # pragma: no cover
    redis = None  # type: ignore[misc]
    REDIS_AVAILABLE = False

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[misc]
    PSYCOPG2_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except Exception:  # pragma: no cover
    httpx = None  # type: ignore[misc]
    HTTPX_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except Exception:  # pragma: no cover
    psutil = None  # type: ignore[misc]
    PSUTIL_AVAILABLE = False

try:
    import jinja2
    JINJA2_AVAILABLE = True
except Exception:  # pragma: no cover
    jinja2 = None  # type: ignore[misc]
    JINJA2_AVAILABLE = False


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
DEFAULT_MCP_ENABLE = os.getenv("MCP_ENABLE", "false").lower() == "true"
DEFAULT_MCP_SERVERS_JSON = os.getenv("MCP_SERVERS", "[]")
DEFAULT_MCP_TIMEOUT_SECONDS = int(os.getenv("MCP_TIMEOUT_SECONDS", "30"))
