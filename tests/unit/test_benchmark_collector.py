import time
from unittest.mock import MagicMock

import pytest

from aio.benchmark.collector import BenchmarkCollector, BenchmarkSnapshot
from aio.layers.observability import ObservabilityLayer


@pytest.fixture
def obs_cfg():
    from aio.config.models import ObservabilityConfig

    return ObservabilityConfig(prometheus_port=0, log_level="DEBUG")


class TestBenchmarkCollector:
    def test_wraps_latency(self, obs_cfg):
        obs = ObservabilityLayer(obs_cfg)
        col = BenchmarkCollector(obs, enable_memory=False)
        col.install()
        try:
            obs.record_latency("node_a", 0.1)
            obs.record_latency("node_a", 0.2)
            obs.record_latency("node_b", 0.05)
            snap = col.snapshot()
            assert "node_a" in snap.node_snapshots
            assert snap.node_snapshots["node_a"].count == 2
            assert snap.node_snapshots["node_a"].p50 == pytest.approx(0.15, abs=0.01)
            assert snap.node_snapshots["node_b"].count == 1
        finally:
            col.uninstall()

    def test_wraps_count_node(self, obs_cfg):
        obs = ObservabilityLayer(obs_cfg)
        col = BenchmarkCollector(obs, enable_memory=False)
        col.install()
        try:
            obs.count_node("node_a", "success")
            obs.count_node("node_a", "failure")
            snap = col.snapshot()
            assert snap.node_snapshots["node_a"].statuses == ["success", "failure"]
        finally:
            col.uninstall()

    def test_e2e_and_throughput(self, obs_cfg):
        obs = ObservabilityLayer(obs_cfg)
        col = BenchmarkCollector(obs, enable_memory=False)
        col.install()
        try:
            col.record_e2e(0.5)
            col.record_e2e(0.5)
            snap = col.snapshot()
            assert snap.iterations == 2
            assert snap.throughput == pytest.approx(2.0, abs=0.1)
        finally:
            col.uninstall()

    def test_reset_clears_data(self, obs_cfg):
        obs = ObservabilityLayer(obs_cfg)
        col = BenchmarkCollector(obs, enable_memory=False)
        col.install()
        try:
            obs.record_latency("node_a", 0.1)
            col.record_e2e(0.5)
            col.reset()
            snap = col.snapshot()
            assert snap.iterations == 0
            assert not snap.node_snapshots
        finally:
            col.uninstall()

    def test_uninstall_restores_original(self, obs_cfg):
        obs = ObservabilityLayer(obs_cfg)
        col = BenchmarkCollector(obs, enable_memory=False)
        orig = col._original_record_latency
        col.install()
        assert obs.record_latency is not orig
        col.uninstall()
        assert obs.record_latency is orig

    def test_memory_graceful_when_psutil_missing(self, obs_cfg, monkeypatch):
        monkeypatch.setattr("aio.benchmark.collector.PSUTIL_AVAILABLE", False)
        obs = ObservabilityLayer(obs_cfg)
        col = BenchmarkCollector(obs, enable_memory=True)
        col.install()
        try:
            val = col.sample_memory()
            # tracemalloc may or may not return a value depending on state
            assert val is None or isinstance(val, int)
        finally:
            col.uninstall()

    def test_memory_with_psutil(self, obs_cfg, monkeypatch):
        mock_psutil = MagicMock()
        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 12345678
        mock_psutil.Process.return_value = mock_process
        monkeypatch.setattr("aio.benchmark.collector.PSUTIL_AVAILABLE", True)
        monkeypatch.setitem(__import__("sys").modules, "psutil", mock_psutil)
        # Need to patch the import inside collector; easier to patch PSUTIL_AVAILABLE
        # and then re-import or just test via mock on the module
        from aio.benchmark import collector as _col_mod

        monkeypatch.setattr(_col_mod, "PSUTIL_AVAILABLE", True)
        obs = ObservabilityLayer(obs_cfg)
        col = BenchmarkCollector(obs, enable_memory=True)
        # Manually inject mock process since import already happened
        col._process = mock_process
        col.install()
        try:
            val = col.sample_memory()
            assert val == 12345678
            snap = col.snapshot()
            assert snap.memory_samples_bytes == [12345678]
        finally:
            col.uninstall()
