from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, Optional

from ..config.deps import (
    OTEL_AVAILABLE,
    PROMETHEUS_AVAILABLE,
    LANGSMITH_AVAILABLE,
    DEFAULT_SERVICE_NAME,
    DEFAULT_OTEL_ENDPOINT,
)
from ..config.models import ObservabilityConfig


def _flag(name: str, default: bool = False) -> bool:
    """Read a feature flag from ``aio_framework`` if available (so patches
    like ``patch("aio_framework.PROMETHEUS_AVAILABLE", True)`` work),
    otherwise fall back to the value in ``aio.config.deps``."""
    mod = sys.modules.get("aio_framework")
    if mod is not None:
        return getattr(mod, name, default)
    return default


class ObservabilityLayer:
    """Layer 0 — OpenTelemetry tracing, Prometheus metrics, structured logging, and LangSmith.

    This class is instantiated once per graph build and injected into every
    downstream layer so that spans, counters, and gauges are emitted from a
    single coherent source.

    Args:
        config: Layer 0 configuration (endpoint, ports, log level, etc.).
    """

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
        from opentelemetry import trace as _trace
        from opentelemetry.sdk.trace import TracerProvider as _TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor as _BatchSpanProcessor, ConsoleSpanExporter as _ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource as _Resource, SERVICE_NAME as _SERVICE_NAME
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as _OTLPSpanExporter
        resource = _Resource.create({_SERVICE_NAME: self.config.service_name})
        provider = _TracerProvider(resource=resource)
        try:
            exporter = _OTLPSpanExporter(endpoint=self.config.otel_endpoint, insecure=True)
            provider.add_span_processor(_BatchSpanProcessor(exporter))
        except Exception as exc:
            self.logger.warning("OTLP exporter failed (%s); falling back to console.", exc)
            provider.add_span_processor(_BatchSpanProcessor(_ConsoleSpanExporter()))
        _trace.set_tracer_provider(provider)
        self._tracer = _trace.get_tracer("aio")

    def _setup_metrics(self) -> None:
        if not _flag("PROMETHEUS_AVAILABLE", PROMETHEUS_AVAILABLE):
            self.logger.warning("Prometheus client not available; metrics disabled.")
            return
        import aio_framework
        _Counter = aio_framework.Counter
        _Histogram = aio_framework.Histogram
        _Gauge = aio_framework.Gauge
        _start_http_server = aio_framework.start_http_server
        from prometheus_client import CollectorRegistry
        self._registry = CollectorRegistry()
        self.node_latency = _Histogram(
            "aio_node_latency_seconds", "Latency per node", ["node_name"],
            registry=self._registry,
        )
        self.node_counter = _Counter(
            "aio_node_executions_total", "Total node executions", ["node_name", "status"],
            registry=self._registry,
        )
        self.failure_gauge = _Gauge(
            "aio_failure_state", "Current failure state (0=HEALTHY,1=DEGRADED,2=RECOVERING,3=FAILED)",
            registry=self._registry,
        )
        self.context_budget_gauge = _Gauge(
            "aio_context_budget_tokens", "Remaining context budget",
            registry=self._registry,
        )
        if self.config.prometheus_port:
            try:
                _start_http_server(self.config.prometheus_port, registry=self._registry)
                self.logger.info("Prometheus metrics server started on port %d", self.config.prometheus_port)
            except Exception as exc:
                self.logger.warning("Could not start Prometheus server: %s", exc)

    def _setup_langsmith(self) -> None:
        if not LANGSMITH_AVAILABLE or not self.config.enable_langsmith:
            return
        from aio_framework import LangSmithClient as _LangSmithClient
        try:
            self._langsmith = _LangSmithClient()
            self.logger.info("LangSmith client initialized.")
        except Exception as exc:
            self.logger.warning("LangSmith init failed: %s", exc)

    def start_span(self, name: str, trace_id: Optional[str] = None) -> Any:
        """Return an OpenTelemetry span context manager (or a no-op null context).

        Args:
            name: Logical operation name (e.g. ``context.ingest``).
            trace_id: Optional 32-hex trace ID to correlate with the state.

        Returns:
            A context manager that enters/exits the span.
        """
        if self._tracer is None:
            return _NullContext()
        import importlib
        _trace = importlib.import_module("opentelemetry.trace")
        ctx = _trace.set_span_in_context(_trace.NonRecordingSpan(_trace.SpanContext(
            trace_id=int(trace_id or "0" * 32, 16),
            span_id=int(uuid.uuid4().hex[:16], 16),
            is_remote=False,
            trace_flags=_trace.TraceFlags(_trace.TraceFlags.SAMPLED),
        )))
        return self._tracer.start_as_current_span(name, context=ctx)

    def record_latency(self, node_name: str, seconds: float) -> None:
        """Record node execution latency to the Prometheus histogram.

        Args:
            node_name: Name of the LangGraph node.
            seconds: Wall-clock latency in seconds.
        """
        if _flag("PROMETHEUS_AVAILABLE", PROMETHEUS_AVAILABLE) and hasattr(self, "node_latency"):
            self.node_latency.labels(node_name=node_name).observe(seconds)

    def count_node(self, node_name: str, status: str) -> None:
        """Increment the execution counter for a node/status pair.

        Args:
            node_name: Name of the LangGraph node.
            status: Arbitrary status label (``success``, ``failure``, ``blocked``, etc.).
        """
        if _flag("PROMETHEUS_AVAILABLE", PROMETHEUS_AVAILABLE) and hasattr(self, "node_counter"):
            self.node_counter.labels(node_name=node_name, status=status).inc()

    def set_failure_state(self, state: str) -> None:
        """Update the gauge that reflects the current failure state.

        Args:
            state: One of ``HEALTHY``, ``DEGRADED``, ``RECOVERING``, ``FAILED``.
        """
        mapping = {"HEALTHY": 0, "DEGRADED": 1, "RECOVERING": 2, "FAILED": 3}
        if _flag("PROMETHEUS_AVAILABLE", PROMETHEUS_AVAILABLE) and hasattr(self, "failure_gauge"):
            self.failure_gauge.set(mapping.get(state, 0))

    def set_context_budget(self, tokens: int) -> None:
        """Update the gauge that tracks remaining context tokens.

        Args:
            tokens: Remaining token budget.
        """
        if _flag("PROMETHEUS_AVAILABLE", PROMETHEUS_AVAILABLE) and hasattr(self, "context_budget_gauge"):
            self.context_budget_gauge.set(tokens)

    def log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Emit a structured log line with an auto-generated correlation ID.

        Args:
            level: Python logging level constant.
            message: Log message string.
            extra: Optional dictionary merged into the log record.
        """
        extra = extra or {}
        extra.setdefault("correlation_id", str(uuid.uuid4())[:8])
        self.logger.log(level, message, extra=extra)


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
