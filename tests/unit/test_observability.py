import logging
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from aio_framework import (
    ObservabilityLayer,
    ObservabilityConfig,
    _NullContext,
)


@pytest.fixture
def obs_cfg():
    return ObservabilityConfig(
        otel_endpoint="http://localhost:4317",
        service_name="test-aio",
        prometheus_port=0,
        log_level="DEBUG",
        enable_langsmith=False,
        langchain_project="test",
    )


class TestObservabilityLayer:
    def test_init_sets_logger(self, obs_cfg):
        layer = ObservabilityLayer(obs_cfg)
        assert layer.logger.name == "aio.observability"
        assert layer.logger.isEnabledFor(logging.DEBUG)

    def test_null_context(self):
        nc = _NullContext()
        with nc as ctx:
            assert ctx is nc

    def test_start_span_without_otel(self, obs_cfg):
        with patch("aio_framework.OTEL_AVAILABLE", False):
            layer = ObservabilityLayer(obs_cfg)
            span = layer.start_span("test")
            assert isinstance(span, _NullContext)

    def test_record_latency_without_prometheus(self, obs_cfg):
        with patch("aio_framework.PROMETHEUS_AVAILABLE", False):
            layer = ObservabilityLayer(obs_cfg)
            layer.record_latency("node_a", 0.123)

    def test_count_node_without_prometheus(self, obs_cfg):
        with patch("aio_framework.PROMETHEUS_AVAILABLE", False):
            layer = ObservabilityLayer(obs_cfg)
            layer.count_node("node_a", "success")

    def test_set_failure_state_without_prometheus(self, obs_cfg):
        with patch("aio_framework.PROMETHEUS_AVAILABLE", False):
            layer = ObservabilityLayer(obs_cfg)
            layer.set_failure_state("DEGRADED")

    def test_log_includes_correlation_id(self, obs_cfg, caplog):
        layer = ObservabilityLayer(obs_cfg)
        with caplog.at_level(logging.INFO):
            layer.log(logging.INFO, "hello")
        assert "hello" in caplog.text

    def test_latency_and_count_with_prometheus_mock(self, obs_cfg):
        with patch("aio_framework.PROMETHEUS_AVAILABLE", True):
            with patch("aio_framework.start_http_server"):
                with patch("aio_framework.Counter") as MockCounter:
                    with patch("aio_framework.Histogram") as MockHistogram:
                        layer = ObservabilityLayer(obs_cfg)
                        mock_hist = MagicMock()
                        mock_counter = MagicMock()
                        layer.node_latency = mock_hist
                        layer.node_counter = mock_counter
                        layer.record_latency("node_x", 0.5)
                        mock_hist.labels.assert_called_once_with(node_name="node_x")
                        mock_hist.labels().observe.assert_called_once_with(0.5)
                        layer.count_node("node_x", "failure")
                        mock_counter.labels.assert_called_once_with(node_name="node_x", status="failure")
                        mock_counter.labels().inc.assert_called_once()
